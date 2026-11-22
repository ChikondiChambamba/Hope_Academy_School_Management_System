"""Importing students from Excel / CSV, against a temporary SQLite database."""
import csv
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook

from tests.test_sqlite_integration import SQLiteTestCase
from utils import student_import as si

HEADERS = ["student_code", "student_name", "class", "birth_date", "parent_name",
           "parent_phone", "enrollment_date", "status"]


class StudentImportTestCase(SQLiteTestCase):
    def setUp(self):
        super().setUp()
        self.existing_id = self.add_student("Ama", cls="Grade 1")       # Ama Banda, Grade 1
        self.existing_code = self.db.execute_query("SELECT student_code FROM students", fetch=True)[0]["student_code"]
        self.db.execute_query("INSERT INTO classes (class_name) VALUES ('Grade 1')")

    def workbook(self, rows, name="students.xlsx", separator=True):
        wb = Workbook()
        ws = wb.active
        ws.append(["Hope Academy - student list"])          # title above the header row
        ws.append(HEADERS)
        if separator:
            ws.append(["-" * 12] * len(HEADERS))             # like the exported list
        for row in rows:
            ws.append(row)
        path = self.tmp / name
        wb.save(path)
        return path

    def sample(self):
        return self.workbook([
            ["", "Chikondi Grace Phiri", "grade 1", datetime(2017, 5, 2), "Grace Phiri", 999123456,
             datetime(2024, 1, 10), "Active"],                                            # new; class case fixed
            ["", "Thoko Mwale", "Grade 2", "14/03/2016", "John Mwale", "0888123456", "2024-01-10", "Inactive"],
            ["", "Thoko Mwale", "Grade 2", "14/03/2016", "John Mwale", "0888123456", "2024-01-10", "Active"],
            ["", "Madonna", "Grade 2", "2016-01-01", "", "", "2024-01-10", ""],          # no surname
            ["", "Pemphero Banda", "Grade 3", "31/31/2015", "", "", "2024-01-10", ""],   # bad date
            ["", "Ama Banda", "Grade 1", "2016-03-01", "Parent", "0999123456", "2024-01-10", "Active"],
        ])

    def test_plan_reads_the_sheet_and_explains_every_row(self):
        plan = si.plan_student_import(self.sample())
        by_row = {r.row_number: r for r in plan.rows}
        self.assertEqual([by_row[n].action for n in sorted(by_row)],
                         [si.NEW, si.NEW, si.SKIP, si.ERROR, si.ERROR, si.SKIP])
        first = by_row[4].student
        self.assertEqual((first.first_name, first.last_name), ("Chikondi Grace", "Phiri"))
        self.assertEqual(first.class_name, "Grade 1")                 # matched the existing spelling
        self.assertEqual(first.parent_phone, "0999123456")            # leading zero restored
        self.assertEqual(first.birth_date, date(2017, 5, 2))
        self.assertFalse(by_row[5].student.is_active)
        self.assertEqual(by_row[5].student.birth_date, date(2016, 3, 14))   # day-first date
        self.assertIn("surname", by_row[7].message)
        self.assertIn("not a date", by_row[8].message)
        self.assertIn(self.existing_code, by_row[9].message)
        # nothing was written while planning
        self.assertEqual(self.db.execute_query("SELECT COUNT(*) AS n FROM students", fetch=True)[0]["n"], 1)

    def test_apply_saves_new_students_and_classes(self):
        plan = si.plan_student_import(self.sample())
        result = si.apply_student_import(plan)
        self.assertEqual((result["added"], result["updated"], result["failed"]), (2, 0, []))
        rows = self.db.execute_query("SELECT first_name, last_name, class, student_code, is_active "
                                     "FROM students ORDER BY student_id", fetch=True)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["student_code"].startswith("STU") for r in rows))
        self.assertEqual(len({r["student_code"] for r in rows}), 3)
        classes = {r["class_name"] for r in self.db.execute_query("SELECT class_name FROM classes", fetch=True)}
        self.assertEqual(classes, {"Grade 1", "Grade 2"})            # no duplicate 'grade 1'
        # importing the same file again adds nobody
        again = si.plan_student_import(self.sample())
        self.assertEqual(again.count(si.NEW), 0)

    def test_code_clash_with_existing_student(self):
        path = self.workbook([["STU9999", "Ama Banda", "Grade 1", "2016-03-01", "", "", "2024-01-10", ""]])
        row = si.plan_student_import(path).rows[0]
        self.assertEqual(row.action, si.ERROR)
        self.assertIn(f"already exists as {self.existing_code}", row.message)

    def test_old_inactive_record_and_new_record_are_both_kept(self):
        # Real data: a pupil re-entered under a new code, the old record kept inactive.
        path = self.workbook([
            ["STU5001", "Favour Yohane", "Grade 3", "", "Mr and Mrs", "", "2024-01-10", "Inactive"],
            ["STU5002", "Favour Yohane", "Grade 3", "", "Mr Yohane", "", "2024-09-01", "Active"],
        ])
        plan = si.plan_student_import(path)
        self.assertEqual([r.action for r in plan.rows], [si.NEW, si.NEW])
        self.assertEqual(si.apply_student_import(plan)["added"], 2)
        again = si.plan_student_import(path)
        self.assertEqual([r.action for r in again.rows], [si.SKIP, si.SKIP])     # found by their codes

    def test_two_active_pupils_with_the_same_name_are_flagged(self):
        path = self.workbook([
            ["STU5001", "Favour Yohane", "Grade 3", "", "", "", "2024-01-10", "Active"],
            ["STU5002", "Favour Yohane", "Grade 3", "", "", "", "2024-09-01", "Active"],
        ])
        plan = si.plan_student_import(path)
        self.assertEqual([r.action for r in plan.rows], [si.NEW, si.ERROR])
        self.assertIn("mark one Inactive", plan.rows[1].message)

    def test_update_existing(self):
        path = self.workbook([[self.existing_code, "Ama Banda", "Grade 1", "2016-03-01", "New Parent",
                               "0888000111", "2024-01-10", "Active"]])
        self.assertEqual(si.plan_student_import(path).rows[0].action, si.SKIP)
        plan = si.plan_student_import(path, update_existing=True)
        self.assertEqual(plan.rows[0].action, si.UPDATE)
        self.assertEqual(si.apply_student_import(plan)["updated"], 1)
        row = self.db.execute_query("SELECT parent_name, parent_phone FROM students WHERE student_id = %s",
                                    (self.existing_id,), fetch=True)[0]
        self.assertEqual((row["parent_name"], row["parent_phone"]), ("New Parent", "0888000111"))

    def test_csv_and_column_variations(self):
        path = self.tmp / "students.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["First Name", "Surname", "Grade", "DOB", "Guardian", "Phone"])
            writer.writerow(["Kondwani", "Chirwa", "Grade 4", "2014-07-09", "Mary Chirwa", "0999555444"])
        plan = si.plan_student_import(path)
        self.assertEqual(plan.rows[0].action, si.NEW)
        self.assertEqual(plan.rows[0].student.last_name, "Chirwa")
        self.assertIn("today", plan.rows[0].message)                 # no enrollment column

    def test_missing_required_columns_is_explained(self):
        wb = Workbook()
        wb.active.append(["code", "phone"])
        wb.active.append(["STU1", "0999"])
        path = self.tmp / "bad.xlsx"
        wb.save(path)
        with self.assertRaises(ValueError) as ctx:
            si.plan_student_import(path)
        self.assertIn("student_name", str(ctx.exception))

    def test_template_round_trip(self):
        template = si.write_template(self.tmp / "template.xlsx")
        plan = si.plan_student_import(template)
        self.assertEqual([r.action for r in plan.rows], [si.NEW])    # the example row is valid
        self.assertEqual(plan.rows[0].student.parent_phone, "0999123456")


class ParsingTestCase(SQLiteTestCase):
    def test_dates(self):
        self.assertEqual(si.parse_date("01/03/2015"), date(2015, 3, 1))     # day first
        self.assertEqual(si.parse_date("2015-03-01 00:00:00"), date(2015, 3, 1))
        self.assertEqual(si.parse_date(42064), date(2015, 3, 1))            # Excel serial number
        self.assertIsNone(si.parse_date(""))
        with self.assertRaises(ValueError):
            si.parse_date("next week")

    def test_names_status_phone(self):
        self.assertEqual(si.split_name("  Chikondi  Grace Banda "), ("Chikondi Grace", "Banda"))
        self.assertFalse(si.parse_status("Withdrawn"))
        self.assertTrue(si.parse_status(None))
        self.assertEqual(si.parse_phone(888123456.0), "0888123456")
        self.assertEqual(si.parse_phone("+265 999 123 456"), "+265 999 123 456")
