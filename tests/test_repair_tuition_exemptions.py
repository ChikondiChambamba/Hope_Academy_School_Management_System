"""The one-off repair removes only exemptions made by the old automatic tuition rule."""
import importlib.util
import sys
from datetime import date
from pathlib import Path

from tests.test_sqlite_integration import SQLiteTestCase, YEAR
import config

C = config.Config
spec = importlib.util.spec_from_file_location(
    "repair_tuition_exemptions", Path(__file__).parents[1] / "scripts" / "repair_tuition_exemptions.py")
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class RepairTestCase(SQLiteTestCase):
    def exempt(self, student, fee, reason):
        self.db.execute_query("INSERT INTO student_fee_exemptions (student_id, fee_type_id, reason) VALUES (%s,%s,%s)",
                              (student, fee, reason))

    def reasons(self):
        return sorted(r["reason"] for r in self.db.execute_query("SELECT reason FROM student_fee_exemptions", fetch=True))

    def test_removes_only_automatic_tuition_exemptions(self):
        C.TERM_SCHEDULE = {**C.TERM_SCHEDULE, "Term 2": {"start_date": "2026-01-05", "end_date": "2026-04-02"}}
        early = self.add_student("Early")                                    # enrolled 2024 (see add_student)
        late = self.add_student("Late")
        self.db.execute_query("UPDATE students SET enrollment_date = %s WHERE student_id = %s", (date(2026, 5, 4), late))
        t2 = self.add_fee_type("Primary Tuition Fee", 85000, term="Term 2")
        uniform = self.add_fee_type("Uniform", 40000, term="Term 2")
        self.exempt(early, t2, "Exempted because tuition 11 paid")          # wrong: early pupil owes it
        self.exempt(late, t2, "Exempted because tuition 11 paid")           # joined after Term 2: keep
        self.exempt(early, uniform, "Bursary")                              # deliberate: keep

        sys.argv = ["repair"]
        repair.main()                                                       # report only
        self.assertEqual(len(self.reasons()), 3)

        sys.argv = ["repair", "--apply"]
        repair.main()
        self.assertEqual(self.reasons(), ["Bursary", "Exempted because tuition 11 paid"])
        kept = self.db.execute_query("SELECT student_id FROM student_fee_exemptions WHERE reason LIKE 'Exempted%%'",
                                     fetch=True)
        self.assertEqual([r["student_id"] for r in kept], [late])
        saved = list(Path(C.PATHS["backups"]).glob("removed_tuition_exemptions_*.csv"))
        self.assertEqual(len(saved), 1)
