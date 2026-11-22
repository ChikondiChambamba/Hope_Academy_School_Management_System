"""database/schema.sql must be safe and parseable without a server."""
import unittest

from tests import _support  # noqa: F401  (must be imported first)
import setup_database


class SplitSqlTestCase(unittest.TestCase):
    def test_delimiter_blocks_stay_whole(self):
        script = (
            "CREATE TABLE a (id INT);\n"
            "-- comment\n"
            "DELIMITER $$\n"
            "CREATE TRIGGER t BEFORE INSERT ON a FOR EACH ROW\n"
            "BEGIN\n"
            "    SET NEW.id = 1;\n"
            "END$$\n"
            "DELIMITER ;\n"
            "CREATE TABLE b (id INT);\n"
        )
        statements = setup_database.split_sql_script(script)
        self.assertEqual(len(statements), 3)
        self.assertIn("SET NEW.id = 1;", statements[1])
        self.assertTrue(statements[1].rstrip().endswith("END"))


class SchemaFileTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = setup_database.SCHEMA_FILE.read_text(encoding="utf-8-sig")
        cls.statements = setup_database.split_sql_script(cls.text)

    def test_schema_never_drops_data(self):
        for statement in self.statements:
            self.assertNotRegex(statement.upper(), r"\bDROP\s+(DATABASE|TABLE)\b")

    def test_schema_does_not_hardcode_database(self):
        for statement in self.statements:
            self.assertFalse(statement.upper().startswith(("USE ", "CREATE DATABASE")), statement[:60])

    def test_every_routine_is_a_single_statement(self):
        routines = [s for s in self.statements if s.upper().startswith(("CREATE TRIGGER", "CREATE PROCEDURE"))]
        self.assertGreaterEqual(len(routines), 3)
        for routine in routines:
            self.assertTrue(routine.rstrip().upper().endswith("END"), routine[:60])

    def test_no_empty_inserts(self):
        for statement in self.statements:
            if statement.upper().startswith("INSERT"):
                self.assertNotRegex(statement, r"VALUES\s*$")

    def test_tables_used_by_code_are_defined(self):
        upper = self.text.upper()
        for table in ("AUDIT_LOG", "EXPENSE_CATEGORIES", "TEACHER_SALARY_MONTHLY", "TERM_ROLLOVER_RUNS"):
            self.assertIn(f"TABLE {table}", upper.replace("IF NOT EXISTS ", ""), table)

    def test_payment_methods_match_ui(self):
        self.assertIn("'Mobile money'", self.text)


if __name__ == "__main__":
    unittest.main()
