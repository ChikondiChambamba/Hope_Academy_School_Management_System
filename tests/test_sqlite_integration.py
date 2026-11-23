"""The application's real SQL, run against a temporary SQLite database.

These tests exercise the models, rollover, payroll, reports and backup code
end to end on "on this computer" storage, which is what most installations use.
"""
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tests import _support
import config
from database.sqlite_backend import SQLiteBackend, is_school_database

C = config.Config
YEAR = "2025-2026"


class SQLiteTestCase(unittest.TestCase):
    """Fresh database per test, with the app configured for SQLite storage."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hope_sqlite_"))
        self._saved = {k: getattr(C, k) for k in (
            "DB_BACKEND", "SQLITE_PATH", "CURRENT_ACADEMIC_YEAR", "CURRENT_TERM", "TERM_SCHEDULE",
            "PREVIOUS_ACADEMIC_YEAR", "PREVIOUS_TERM", "ACADEMIC_YEAR_START_DATE", "ACADEMIC_YEAR_END_DATE",
            "TERM_START_DATE", "TERM_END_DATE", "PATHS")}
        C.DB_BACKEND = "sqlite"
        C.SQLITE_PATH = str(self.tmp / "school_data.db")
        C.PATHS = {**C.PATHS, "backups": self.tmp / "backups", "exports": self.tmp / "exports",
                   "reports": self.tmp / "reports"}
        C.CURRENT_ACADEMIC_YEAR, C.CURRENT_TERM = YEAR, "Term 3"
        C.TERM_SCHEDULE = {t: {"start_date": None, "end_date": None} for t in C.TERMS}
        self.db = SQLiteBackend(C.SQLITE_PATH)
        self.db.prepare()
        _support.use_database(self.db)
        from database import queries
        queries._HAS_STUDENT_IS_NEW = None

    def tearDown(self):
        _support.reset_database()
        self.db.close()
        for key, value in self._saved.items():
            setattr(C, key, value)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers
    def add_student(self, first, cls="Std 1", is_new=False):
        from models.student import Student
        student = Student(first_name=first, last_name="Banda", class_name=cls, birth_date=date(2016, 3, 1),
                          parent_name="Parent", parent_phone="0999123456", enrollment_date=date(2024, 1, 10),
                          is_new=is_new)
        ok, msg = student.save()
        self.assertTrue(ok, msg)
        return student.student_id

    def add_fee_type(self, name, amount, term="Term 3", year=YEAR):
        from models.finance import FeeType
        fee = FeeType(fee_name=name, amount=amount, term=term, academic_year=year, is_required=True)
        ok, msg = fee.save()
        self.assertTrue(ok, msg)
        return fee.fee_type_id

    def pay(self, student_id, fee_type_id, amount, method="Mobile money"):
        from models.finance import FeePayment
        payment = FeePayment(student_id=student_id, fee_type_id=fee_type_id, amount_paid=amount,
                             payment_date=date.today(), payment_method=method)
        ok, msg = payment.save()
        self.assertTrue(ok, msg)
        return payment


class SchemaTestCase(SQLiteTestCase):
    def test_schema_matches_mysql_tables(self):
        import re
        mysql_tables = set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)",
                                      (Path(__file__).parents[1] / "database" / "schema.sql").read_text(encoding="utf-8")))
        self.assertEqual(set(self.db.list_tables()) - {"sqlite_sequence"}, mysql_tables)

    def test_prepare_is_idempotent_and_versioned(self):
        self.db.prepare()
        from database.sqlite_backend import SCHEMA_VERSION
        self.assertEqual(self.db.execute_query("PRAGMA user_version", fetch=True)[0]["user_version"], SCHEMA_VERSION)
        self.assertTrue(self.db.integrity_ok())

    def test_foreign_keys_are_enforced(self):
        with self.assertRaises(Exception):
            self.db.execute_query("INSERT INTO student_fees (student_id, fee_type_id, amount_paid, payment_date) "
                                  "VALUES (999, 999, 1, %s)", (date.today(),))


class ModelsTestCase(SQLiteTestCase):
    def test_students_and_teachers(self):
        from models.student import Student
        from models.teacher import TeacherManager
        sid = self.add_student("Chikondi")
        self.assertEqual(Student.get_by_id(sid).first_name, "Chikondi")
        self.assertEqual(len(Student.search("chik")), 1)              # case-insensitive, like MySQL
        self.assertEqual(len(Student.get_by_class("STD 1")), 1)
        ok, msg, teacher = TeacherManager.create_teacher({
            "first_name": "Eunice", "last_name": "Mwale", "phone": "0888123456",
            "hire_date": "2024-01-05", "salary_amount": 150000, "allowance_amount": 20000})
        self.assertTrue(ok, msg)

    def test_payments_get_unique_daily_receipts(self):
        sid = self.add_student("Ama")
        fid = self.add_fee_type("Tuition", 85000)
        first, second = self.pay(sid, fid, 1000), self.pay(sid, fid, 2000)
        self.assertNotEqual(first.receipt_number, second.receipt_number)
        self.assertTrue(first.receipt_number.endswith("-0001"), first.receipt_number)
        self.assertTrue(second.receipt_number.endswith("-0002"), second.receipt_number)

    def test_expenses_are_term_scoped(self):
        from models.finance import Expense
        ok, msg = Expense(description="Chalk", amount=5000, category="Stationery").save()
        self.assertTrue(ok, msg)
        self.assertEqual(Expense.get_term_expense_total(YEAR, "Term 3"), 5000)
        self.assertEqual(Expense.get_term_expense_total(YEAR, "Term 1"), 0)

    def test_balances(self):
        from models.finance import FinancialManager
        sid = self.add_student("Ama")
        fid = self.add_fee_type("Exam Fee", 15000)
        self.pay(sid, fid, 5000)
        row = next(r for r in FinancialManager.get_student_balances(YEAR, term="Term 3") if r["student_id"] == sid)
        self.assertEqual(row["total_fees"], 15000)
        self.assertEqual(row["balance"], 10000)
        summary = FinancialManager.get_term_financial_summary(YEAR, "Term 3")
        self.assertIsInstance(summary, dict)

    def test_balance_cache_never_serves_stale_figures(self):
        from models.finance import FinancialManager
        sid = self.add_student("Ama")
        fid = self.add_fee_type("Exam Fee", 15000)
        balance = lambda: next(r["balance"] for r in FinancialManager.get_student_balances(YEAR, term="Term 3")
                               if r["student_id"] == sid)
        self.assertEqual(balance(), 15000)
        generation = self.db.write_generation
        self.assertEqual(balance(), 15000)                      # served from cache: no writes in between
        self.assertEqual(self.db.write_generation, generation)
        self.pay(sid, fid, 4000)                                # any write invalidates
        self.assertEqual(balance(), 11000)
        rows = FinancialManager.get_student_balances(YEAR, term="Term 3")
        rows[0]["balance"] = -1                                 # callers get copies
        self.assertEqual(balance(), 11000)

    def test_fee_types_with_class_scope(self):
        from models.finance import FinancialManager
        fid = self.add_fee_type("Lab Fee", 3000)
        cid = self.db.execute_query("INSERT INTO classes (class_name) VALUES ('Std 1')")
        self.db.execute_query("INSERT IGNORE INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s,%s,%s)",
                              (fid, cid, YEAR))
        self.db.execute_query("INSERT IGNORE INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s,%s,%s)",
                              (fid, cid, YEAR))
        templates = FinancialManager._get_term_fee_templates(YEAR, "Term 3")
        lab = next(t for t in templates if t["fee_name"] == "Lab Fee")
        self.assertEqual(lab["class_names"], ["std 1"])
        self.assertEqual(lab["class_ids"], [cid])

    def test_year_end_rollover_with_credit(self):
        from models.finance import FinancialManager
        owes, overpaid = self.add_student("Owes"), self.add_student("Overpaid")
        fid = self.add_fee_type("Exam Fee", 15000)
        self.pay(owes, fid, 5000)
        self.pay(overpaid, fid, 20000)
        result = FinancialManager.execute_term_rollover(YEAR, "Term 3", term_start_date="2026-09-07")
        self.assertEqual((result["to_academic_year"], result["to_term"]), ("2026-2027", "Term 1"))
        carried = {r["student_id"]: float(r["carried_balance"]) for r in self.db.execute_query(
            "SELECT student_id, carried_balance FROM student_term_fee_rollovers", fetch=True)}
        self.assertEqual(carried, {owes: 10000, overpaid: -5000})
        self.assertEqual((C.CURRENT_ACADEMIC_YEAR, C.CURRENT_TERM), ("2026-2027", "Term 1"))
        balances = {r["student_id"]: r["balance"] for r in FinancialManager.get_student_balances("2026-2027", term="Term 1")}
        self.assertEqual(balances, {owes: 25000, overpaid: 10000})
        self.assertIsNotNone(FinancialManager.get_latest_rollover_run().get("completed_at"))

    def test_monthly_payroll_upsert(self):
        from models.finance import FinancialManager
        from models.teacher import TeacherManager
        ok, msg, teacher = TeacherManager.create_teacher({
            "first_name": "Eunice", "last_name": "Mwale", "phone": "0888123456",
            "hire_date": "2024-01-05", "salary_amount": 150000, "allowance_amount": 20000})
        self.assertTrue(ok, msg)
        FinancialManager.generate_monthly_salary_snapshot("2026-06")
        FinancialManager.generate_monthly_salary_snapshot("2026-06")   # regenerating updates, never duplicates
        rows = self.db.execute_query("SELECT * FROM teacher_salary_monthly", fetch=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["gross_salary"], 170000)

    def test_inventory(self):
        from models.inventory import InventoryItem, InventoryManager
        item = InventoryItem(item_name="Chalk", category="Stationery", quantity=10, unit_price=250,
                             min_quantity=2, max_quantity=50)
        ok, msg = item.save()
        self.assertTrue(ok, msg)
        ok, msg = InventoryManager.use_item(item.item_id, 4)
        self.assertTrue(ok, msg)
        stored = InventoryItem.get_by_id(item.item_id)
        self.assertEqual((stored.quantity, stored.total_value), (6, 1500))

    def test_attendance(self):
        from models.attendance import Attendance
        sid = self.add_student("Ama")
        ok, msg = Attendance(student_id=sid, attendance_date=date.today(), status="Present").save()
        self.assertTrue(ok, msg)
        self.assertEqual(len(Attendance.get_by_date(date.today())), 1)

    def test_dashboard_statistics_query(self):
        from database.queries import Queries
        self.add_student("Ama")
        stats = self.db.execute_query(Queries.GET_DASHBOARD_STATS, fetch=True)
        self.assertTrue(stats)


class ReportsTestCase(SQLiteTestCase):
    def test_pdf_reports_generate(self):
        from reports.generators import student_reports, inventory_reports
        from reports.generators import financial_reports
        sid = self.add_student("Ama")
        fid = self.add_fee_type("Tuition", 85000)
        self.pay(sid, fid, 50000)
        out = Path(C.PATHS["reports"]); out.mkdir(parents=True, exist_ok=True)
        for name, fn, kwargs in [
            ("students", student_reports.generate_student_list_report, {}),
            ("attendance", student_reports.generate_attendance_summary_report, {}),
            ("inventory", inventory_reports.generate_inventory_list_report, {}),
            ("low_stock", inventory_reports.generate_low_stock_report, {}),
            ("fees", financial_reports.generate_student_fees_report, {"academic_year": YEAR, "term": "Term 3"}),
            ("collection", financial_reports.generate_fee_collection_report, {}),
            ("expenses", financial_reports.generate_expense_report, {"academic_year": YEAR, "term": "Term 3"}),
            ("summary", financial_reports.generate_financial_summary_report, {"academic_year": YEAR, "term": "Term 3"}),
        ]:
            target = out / f"{name}.pdf"
            fn(str(target), **kwargs)
            self.assertTrue(target.exists() and target.stat().st_size > 0, name)


class BackupTestCase(SQLiteTestCase):
    def test_backup_restore_round_trip(self):
        from utils import export_import
        self.add_student("Before")
        backup = self.tmp / "backups" / "manual.db"
        self.assertTrue(export_import.backup_database(str(backup)))
        self.assertTrue(is_school_database(backup))
        self.add_student("After")

        ok, message = export_import.restore_database(str(backup))
        self.assertTrue(ok, message)
        names = [r["first_name"] for r in self.db.execute_query("SELECT first_name FROM students", fetch=True)]
        self.assertEqual(names, ["Before"])
        self.assertTrue(list((self.tmp / "backups").glob("before_restore_*.db")))

    def test_restore_rejects_foreign_files(self):
        from utils import export_import
        junk = self.tmp / "junk.db"
        junk.write_bytes(b"not a database")
        ok, _ = export_import.restore_database(str(junk))
        self.assertFalse(ok)

    def test_automatic_backup_once_per_day_and_pruned(self):
        from utils import export_import
        folder = self.tmp / "backups"; folder.mkdir(parents=True, exist_ok=True)
        for day in range(1, 20):
            (folder / f"auto_202601{day:02d}.db").write_bytes(b"")
        self.assertIsNotNone(export_import.run_automatic_backup())
        self.assertIsNone(export_import.run_automatic_backup())
        self.assertEqual(len(list(folder.glob("auto_*.db"))), export_import.AUTO_BACKUPS_KEPT)

    def test_export_and_maintenance(self):
        from utils import export_import
        from utils.helpers import run_database_maintenance
        self.add_student("Ama")
        folder = export_import.export_all_data(str(self.tmp / "exports"))
        self.assertTrue((folder / "students.csv").exists())
        self.assertEqual(run_database_maintenance()[0], True)
        self.assertEqual(len(self.db.execute_query("SELECT * FROM students", fetch=True)), 1)


if __name__ == "__main__":
    unittest.main()
