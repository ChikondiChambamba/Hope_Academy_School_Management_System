"""SQLite translation layer: MySQL-dialect SQL must behave the same on SQLite."""
import shutil
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from tests import _support
from database.sqlite_backend import SQLiteBackend, translate, _date_format, _concat


class TranslateTestCase(unittest.TestCase):
    def test_placeholders_and_escaped_percent(self):
        self.assertEqual(translate("SELECT * FROM t WHERE a = %s AND b LIKE '%%x%%'"),
                         "SELECT * FROM t WHERE a = ? AND b LIKE '%x%'")

    def test_insert_ignore(self):
        self.assertEqual(translate("INSERT IGNORE INTO t (a) VALUES (%s)"), "INSERT OR IGNORE INTO t (a) VALUES (?)")

    def test_mysql_functions(self):
        self.assertIsNone(_concat("a", None))                       # MySQL: NULL if any part is NULL
        self.assertEqual(_concat("Std ", 1), "Std 1")
        self.assertEqual(_date_format("2026-03-07", "%Y-%m"), "2026-03")
        self.assertEqual(_date_format("2026-03-07 14:05:09", "%d/%m/%Y %H:%i"), "07/03/2026 14:05")


class BackendBehaviourTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db = SQLiteBackend(self.tmp / "t.db")
        self.db.prepare()
        self.sid = self.db.execute_query(
            "INSERT INTO students (student_code, first_name, last_name, class, enrollment_date) VALUES (%s,%s,%s,%s,%s)",
            ("S1", "Ama", "Phiri", "Std 1", date(2024, 1, 10)))

    def tearDown(self):
        _support.reset_database()
        self.db.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dates_come_back_as_python_dates(self):
        row = self.db.execute_query("SELECT enrollment_date, created_at FROM students", fetch=True)[0]
        self.assertIsInstance(row["enrollment_date"], date)
        self.assertIsInstance(row["created_at"], datetime)

    def test_text_compares_case_insensitively_like_mysql(self):
        rows = self.db.execute_query("SELECT * FROM students WHERE class = %s AND first_name = %s", ("STD 1", "ama"), fetch=True)
        self.assertEqual(len(rows), 1)

    def test_insert_returns_id_and_other_statements_zero(self):
        fee = self.db.execute_query("INSERT INTO fee_types (fee_name, amount, academic_year) VALUES ('T', 1, 'Y')")
        self.assertGreater(fee, 0)
        self.assertGreater(self.db.execute_query("INSERT IGNORE INTO student_fee_exemptions (student_id, fee_type_id) VALUES (%s,%s)", (self.sid, fee)), 0)
        self.assertEqual(self.db.execute_query("INSERT IGNORE INTO student_fee_exemptions (student_id, fee_type_id) VALUES (%s,%s)", (self.sid, fee)), 0)
        self.assertEqual(self.db.execute_query("UPDATE students SET class = 'Std 2'"), 0)

    def test_write_generation_moves_only_on_real_changes(self):
        start = self.db.write_generation
        self.db.execute_query("SELECT * FROM students", fetch=True)
        self.db.execute_query("UPDATE students SET class = 'Std 1' WHERE student_id = -1")   # matches nothing
        self.assertEqual(self.db.write_generation, start)
        self.db.execute_query("UPDATE students SET class = 'Std 2'")
        self.assertGreater(self.db.write_generation, start)

    def test_once_per_session(self):
        self.assertTrue(self.db.once("check"))
        self.assertFalse(self.db.once("check"))
        self.db.close()                      # a new session runs checks again
        self.assertTrue(self.db.once("check"))

    def test_upsert_clause(self):
        sql = "INSERT INTO receipt_sequence (seq_date, seq) VALUES (%s, 1) " + \
              self.db.upsert_clause(("seq_date",), set_sql={"seq": "seq + 1"})
        for _ in range(3):
            self.db.execute_query(sql, ("20260101",))
        self.assertEqual(self.db.execute_query("SELECT seq FROM receipt_sequence", fetch=True)[0]["seq"], 3)

    def test_transaction_rolls_back_on_any_error(self):
        with self.assertRaises(ZeroDivisionError):
            with self.db.transaction() as conn:
                self.db.execute_query_in_transaction(conn, "UPDATE students SET class = 'Std 9'")
                1 / 0
        self.assertEqual(self.db.execute_query("SELECT class FROM students", fetch=True)[0]["class"], "Std 1")

    def test_student_history_logged_once_per_edit(self):
        self.db.execute_query("UPDATE students SET class = 'Std 2' WHERE student_id = %s", (self.sid,))
        self.db.execute_query("UPDATE students SET address = 'Zomba' WHERE student_id = %s", (self.sid,))  # untracked field
        self.assertEqual(self.db.execute_query("SELECT COUNT(*) AS n FROM student_audit_log", fetch=True)[0]["n"], 1)

    def test_models_tolerate_joined_columns(self):
        _support.use_database(self.db)
        from models.finance import FeePayment
        fee = self.db.execute_query("INSERT INTO fee_types (fee_name, amount, academic_year) VALUES ('T', 1, 'Y')")
        self.db.execute_query("INSERT INTO student_fees (student_id, fee_type_id, amount_paid, payment_date, receipt_number) "
                              "VALUES (%s, %s, 500, %s, 'R1')", (self.sid, fee, date.today()))
        payments = FeePayment.get_by_date_range(date(2020, 1, 1), date.today())
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].student_name, "Ama Phiri")
        self.assertEqual(len(FeePayment.get_by_student(self.sid)), 1)


if __name__ == "__main__":
    unittest.main()
