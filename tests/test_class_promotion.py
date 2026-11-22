"""Pupils move up a class when the academic year rolls over; the top class leaves."""
from unittest import mock

from tests.test_sqlite_integration import SQLiteTestCase, YEAR
import config
from models.finance import FinancialManager as FM

C = config.Config


class PromotionRulesTestCase(SQLiteTestCase):
    def test_progression(self):
        self.assertEqual(C.promoted_class("Grade 1"), "Grade 2")
        self.assertEqual(C.promoted_class("grade 6"), "Grade 7")
        self.assertIsNone(C.promoted_class("Grade 7"))
        self.assertEqual(C.promoted_class("Nursery"), "Nursery")      # not in the progression

    def classes(self):
        return {r["first_name"]: (r["class"], r["is_active"]) for r in
                self.db.execute_query("SELECT first_name, class, is_active FROM students", fetch=True)}

    def school(self):
        for name, cls in [("One", "Grade 1"), ("Two", "Grade 2"), ("Six", "Grade 6"), ("Seven", "Grade 7"),
                          ("Tiny", "Nursery")]:
            self.add_student(name, cls=cls)

    def test_year_end_rollover_promotes_and_graduates(self):
        self.school()
        preview = FM.get_term_rollover_preview(YEAR, "Term 3")
        self.assertEqual(preview["promotion"]["promoted_students"], 3)
        self.assertEqual(preview["promotion"]["graduating_students"], 1)
        self.assertIn("Grade 1 -> Grade 2: 1", FM.describe_promotion(preview["promotion"]))
        self.assertEqual(self.classes()["One"], ("Grade 1", 1))      # preview changes nothing

        result = FM.execute_term_rollover(YEAR, "Term 3", term_start_date="2026-09-07")
        self.assertEqual(result["promotion_result"], {"promoted_students": 3, "graduated_students": 1})
        self.assertEqual(self.classes(), {
            "One": ("Grade 2", 1), "Two": ("Grade 3", 1), "Six": ("Grade 7", 1),   # each moved exactly once
            "Seven": ("Grade 7", 0),                                                  # finished school
            "Tiny": ("Nursery", 1),
        })
        names = {r["class_name"] for r in self.db.execute_query("SELECT class_name FROM classes", fetch=True)}
        self.assertTrue({"Grade 2", "Grade 3", "Grade 7"} <= names)

    def test_rollover_within_the_year_changes_no_class(self):
        self.school()
        C.CURRENT_TERM = "Term 1"
        result = FM.execute_term_rollover(YEAR, "Term 1")
        self.assertIsNone(result["promotion_result"])
        self.assertIsNone(result["promotion"])
        self.assertEqual(self.classes()["One"], ("Grade 1", 1))
        self.assertEqual(self.classes()["Seven"], ("Grade 7", 1))

    def test_next_year_fees_follow_the_new_class(self):
        one = self.add_student("One", cls="Grade 1")
        seven = self.add_student("Seven", cls="Grade 7")
        g2 = self.db.execute_query("INSERT INTO classes (class_name) VALUES ('Grade 2')")
        g1 = self.db.execute_query("INSERT INTO classes (class_name) VALUES ('Grade 1')")
        lab = self.add_fee_type("Grade 2 Lab", 3000)                # Term 3 fee only for Grade 2
        self.db.execute_query("INSERT INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s,%s,%s)",
                              (lab, g2, YEAR))
        trip = self.add_fee_type("Grade 1 Trip", 1000)
        self.db.execute_query("INSERT INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s,%s,%s)",
                              (trip, g1, YEAR))
        self.add_fee_type("Exam Fee", 5000)
        preview = FM.get_term_rollover_preview(YEAR, "Term 3")
        rows = {r["student_id"]: r for r in preview["rows"]}
        # One becomes Grade 2: Exam Fee + Grade 2 Lab next year, not the Grade 1 Trip.
        self.assertEqual(rows[one]["new_term_total"], 5000 + 3000)
        # Seven leaves: no fees next year.
        self.assertEqual(rows[seven]["new_term_total"], 0)

    def test_graduate_with_unpaid_fees_is_reported(self):
        seven = self.add_student("Seven", cls="Grade 7")
        fee = self.add_fee_type("Exam Fee", 5000)
        self.pay(seven, fee, 1000)
        preview = FM.get_term_rollover_preview(YEAR, "Term 3")
        self.assertEqual(preview["promotion"]["graduating_with_balance"], 1)
        self.assertEqual(preview["promotion"]["graduating_balance_total"], 4000)
        self.assertTrue(any("graduating" in w for w in preview["warnings"]))
        FM.execute_term_rollover(YEAR, "Term 3")
        owed = self.db.execute_query("SELECT carried_balance FROM student_term_fee_rollovers WHERE student_id = %s",
                                     (seven,), fetch=True)
        self.assertEqual(float(owed[0]["carried_balance"]), 4000)    # kept on the inactive record

    def test_failed_rollover_promotes_nobody(self):
        self.school()
        real_promote = FM._promote_students.__func__

        def promote_then_fail(cls, connection):
            real_promote(cls, connection)            # classes are changed inside the transaction...
            raise RuntimeError("power cut")          # ...then the rollover fails

        with mock.patch.object(FM, "_promote_students", classmethod(promote_then_fail)):
            with self.assertRaises(RuntimeError):
                FM.execute_term_rollover(YEAR, "Term 3")
        self.assertEqual(self.classes()["One"], ("Grade 1", 1))
        self.assertEqual(self.classes()["Seven"], ("Grade 7", 1))


if __name__ == "__main__":
    import unittest
    unittest.main()
