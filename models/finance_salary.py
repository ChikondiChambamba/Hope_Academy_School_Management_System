"""Salary snapshot helpers for finance."""
from datetime import date, datetime
from database.connection import db


class FinanceSalaryMixin:
    @staticmethod
    def _month_bounds(year_month: str) -> tuple[date, date]:
        """Return [start, next_month_start) bounds for YYYY-MM."""
        start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        if start.month == 12:
            end_exclusive = date(start.year + 1, 1, 1)
        else:
            end_exclusive = date(start.year, start.month + 1, 1)
        return start, end_exclusive

    @classmethod
    def generate_monthly_salary_snapshot(cls, year_month: str = None) -> None:
        """Compute and persist salary snapshot for a given month (YYYY-MM)."""
        if not year_month:
            year_month = date.today().strftime("%Y-%m")
        cls._ensure_salary_monthly_table()
        start_date, end_exclusive = cls._month_bounds(year_month)

        db.execute_query(
            """
            INSERT INTO teacher_salary_monthly (
                teacher_id, payroll_month, base_salary, allowance_amount, advances_amount, gross_salary, net_salary
            )
            SELECT
                t.teacher_id,
                %s AS payroll_month,
                COALESCE(t.salary_amount, 0) AS base_salary,
                COALESCE(t.allowance_amount, 0) AS allowance_amount,
                COALESCE(SUM(
                    CASE
                        WHEN tsa.status IN ('Approved', 'Deducted') THEN COALESCE(tsa.advance_amount, 0)
                        ELSE 0
                    END
                ), 0) AS advances_amount,
                (COALESCE(t.salary_amount, 0) + COALESCE(t.allowance_amount, 0)) AS gross_salary,
                (COALESCE(t.salary_amount, 0) + COALESCE(t.allowance_amount, 0) - COALESCE(SUM(
                    CASE
                        WHEN tsa.status IN ('Approved', 'Deducted') THEN COALESCE(tsa.advance_amount, 0)
                        ELSE 0
                    END
                ), 0)) AS net_salary
            FROM teachers t
            LEFT JOIN teacher_salary_advances tsa
              ON tsa.teacher_id = t.teacher_id
             AND tsa.advance_date >= %s
             AND tsa.advance_date < %s
            WHERE t.is_active = 1
            GROUP BY t.teacher_id, t.salary_amount, t.allowance_amount
            """ + db.upsert_clause(
                ("teacher_id", "payroll_month"),
                set_new=("base_salary", "allowance_amount", "advances_amount", "gross_salary", "net_salary"),
                set_sql={"generated_at": "NOW()"},
            ),
            (year_month, start_date, end_exclusive)
        )


