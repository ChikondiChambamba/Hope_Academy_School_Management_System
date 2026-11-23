"""Fee amounts and "new pupils only" come from fee-type settings, never from fee names."""
import sqlite3
from datetime import date

from tests.test_sqlite_integration import SQLiteTestCase, YEAR
from database import sqlite_backend
from models.finance import FeeType, FinancialManager as FM


class FeeRulesTestCase(SQLiteTestCase):
    def balance(self, student_id, term="Term 3"):
        return next(r for r in FM.get_student_balances(YEAR, term=term) if r["student_id"] == student_id)

    def class_fee(self, name, amount, classes, term="Term 3"):
        fid = self.add_fee_type(name, amount, term=term)
        for cls in classes:
            found = self.db.execute_query("SELECT class_id FROM classes WHERE class_name = %s", (cls,), fetch=True)
            cid = found[0]["class_id"] if found else self.db.execute_query(
                "INSERT INTO classes (class_name) VALUES (%s)", (cls,))
            self.db.execute_query("INSERT INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s,%s,%s)",
                                  (fid, cid, YEAR))
        return fid

    def test_changing_the_tuition_amount_changes_what_is_owed(self):
        pupil = self.add_student("Ama", cls="Grade 3")
        tuition = self.class_fee("Primary Tuition Fee", 85000, ["Grade 3"])
        self.assertEqual(self.balance(pupil)["total_fees"], 85000)
        fee = FeeType.get_by_id(tuition)
        fee.amount = 95000                                    # the school raises tuition
        self.assertTrue(fee.save()[0])
        self.assertEqual(self.balance(pupil)["total_fees"], 95000)
        self.assertEqual(FM.get_student_financial_snapshot(pupil, YEAR, "Term 3")["total_due"], 95000)

    def test_nursery_tuition_uses_its_own_fee(self):
        nursery = self.add_student("Tiny", cls="Nursery")
        self.class_fee("Nursery and Reception Tuition", 50000, ["Nursery", "Reception"])
        self.class_fee("Primary Tuition Fee", 85000, ["Grade 3"])
        self.assertEqual(self.balance(nursery)["total_fees"], 50000)   # not a hidden 45,000

    def test_new_pupils_only_is_a_setting_not_a_name(self):
        new = self.add_student("New", is_new=True)
        old = self.add_student("Old", is_new=False)
        kit = FeeType(fee_name="Starter Kit", amount=7000, term="Term 3", academic_year=YEAR, new_students_only=True)
        self.assertTrue(kit.save()[0])
        self.add_fee_type("Registration Fee", 5000)          # named "registration" but not flagged
        self.assertEqual(self.balance(new)["total_fees"], 12000)
        self.assertEqual(self.balance(old)["total_fees"], 5000)

    def test_rollover_copies_the_setting_and_charges_by_it(self):
        self.add_student("Old", is_new=False)
        kit = FeeType(fee_name="Starter Kit", amount=7000, term="Term 3", academic_year=YEAR, new_students_only=True)
        kit.save()
        self.add_fee_type("Exam Fee", 5000)
        FM.execute_term_rollover(YEAR, "Term 3")
        copied = self.db.execute_query("SELECT new_students_only FROM fee_types WHERE academic_year = '2026-2027' "
                                       "AND fee_name = 'Starter Kit'", fetch=True)
        self.assertEqual(copied[0]["new_students_only"], 1)

    def test_paying_tuition_does_not_cancel_other_terms(self):
        pupil = self.add_student("Ama", cls="Grade 3")
        term2 = self.class_fee("Primary Tuition Fee", 85000, ["Grade 3"], term="Term 2")
        term3 = self.class_fee("Primary Tuition Fee", 85000, ["Grade 3"], term="Term 3")
        self.pay(pupil, term3, 85000)
        self.assertEqual(self.db.execute_query("SELECT COUNT(*) AS n FROM student_fee_exemptions", fetch=True)[0]["n"], 0)
        self.assertEqual(self.balance(pupil, "Term 2")["balance"], 85000)          # still owed
        self.assertTrue(term2)


class SchemaUpgradeTestCase(SQLiteTestCase):
    def test_version_1_file_is_upgraded_and_flags_existing_fees(self):
        old_file = self.tmp / "v1.db"
        conn = sqlite3.connect(old_file)
        schema = sqlite_backend._schema_file().read_text(encoding="utf-8")
        conn.executescript(schema.replace("    new_students_only BOOLEAN DEFAULT 0,          -- charged only to pupils marked as new\n", ""))
        conn.execute("PRAGMA user_version = 1")
        conn.executemany("INSERT INTO fee_types (fee_name, amount, academic_year) VALUES (?, ?, ?)",
                         [("Registration Fee", 5000, YEAR), ("Uniform", 40000, YEAR), ("Tuition", 85000, YEAR)])
        conn.commit()
        conn.close()
        upgraded = sqlite_backend.SQLiteBackend(old_file)
        upgraded.prepare()
        rows = {r["fee_name"]: r["new_students_only"] for r in
                upgraded.execute_query("SELECT fee_name, new_students_only FROM fee_types", fetch=True)}
        self.assertEqual(rows, {"Registration Fee": 1, "Uniform": 1, "Tuition": 0})
        self.assertEqual(upgraded.execute_query("PRAGMA user_version", fetch=True)[0]["user_version"], 2)
        upgraded.close()
