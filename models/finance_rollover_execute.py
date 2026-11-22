"""Term rollover execution helpers."""
import json
from typing import Dict, Any, List
import config
from database.connection import db


class FinanceRolloverExecuteMixin:
    @classmethod
    def get_latest_rollover_run(cls) -> Dict[str, Any]:
        """Return the most recent completed rollover run."""
        cls._ensure_term_rollover_tables()
        rows = db.execute_query(
            """
            SELECT *
            FROM term_rollover_runs
            WHERE status = 'COMPLETED'
            ORDER BY COALESCE(completed_at, created_at) DESC, run_id DESC
            LIMIT 1
            """,
            fetch=True
        ) or []
        return rows[0] if rows else {}

    @staticmethod
    def _merge_carry_details(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine carried lines that share a fee name.

        student_term_fee_rollover_items is unique per (student, from, to,
        source_fee_name); a prior carried "Tuition" plus this term's unpaid
        "Tuition" must become one row, or the whole rollover would abort.
        """
        merged: Dict[str, Dict[str, Any]] = {}
        for detail in details:
            amount = float(detail.get('carried_amount') or 0)
            if amount == 0:
                continue
            name = detail.get('fee_name') or 'Carried Balance'
            key = name.strip().lower()
            if key not in merged:
                merged[key] = {**detail, 'fee_name': name, 'carried_amount': 0.0,
                               'expected_amount': 0.0, 'paid_amount': 0.0}
            target = merged[key]
            target['carried_amount'] += amount
            target['expected_amount'] += float(detail.get('expected_amount') or 0)
            target['paid_amount'] += float(detail.get('paid_amount') or 0)
            target['is_required'] = target.get('is_required') or detail.get('is_required')
            if detail.get('fee_type_id') and not target.get('fee_type_id'):
                target['fee_type_id'] = detail.get('fee_type_id')
        return [d for d in merged.values() if d['carried_amount'] != 0]

    @classmethod
    def execute_term_rollover(
        cls,
        academic_year: str = None,
        from_term: str = None,
        to_term: str = None,
        term_start_date: str = None,
        excluded_student_ids=None,
        to_academic_year: str = None,
    ) -> Dict[str, Any]:
        """Close the current term and open the next one, transactionally.

        `academic_year`/`from_term` identify the closing period. The next period
        is derived (see _resolve_rollover_target): after the last term the
        academic year moves forward, e.g. Term 3 2025-2026 -> Term 1 2026-2027.
        """
        from_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        from_term = config.Config.normalize_term_name(from_term or config.Config.CURRENT_TERM)
        to_year, to_term = cls._resolve_rollover_target(from_year, from_term, to_term, to_academic_year)
        year_changes = to_year != from_year
        term_start_date = (term_start_date or '').strip() or None
        if term_start_date:
            start = config.Config.parse_config_date(term_start_date)
            if not start:
                raise ValueError("Term start date must be in YYYY-MM-DD format.")
            _, closing_end = config.Config.get_term_date_bounds(from_term)
            if closing_end and start <= closing_end:
                raise ValueError(
                    f"{to_term} {to_year} cannot start on {start}: {from_term} {from_year} "
                    f"runs until {closing_end}."
                )
        cls._ensure_rollover_year_columns()

        preview = cls._build_term_rollover_preview(
            from_year, from_term, to_year, to_term, excluded_student_ids=excluded_student_ids
        )
        summary = preview['summary']
        executed_by = getattr(config.Config, 'CURRENT_USER', None) or 'System'
        continuing_students_updated = 0

        with db.transaction() as connection:
            def run(sql, params=(), fetch=False):
                return db.execute_query_in_transaction(connection, sql, params, fetch=fetch)

            cloned_fee_types = cls._clone_missing_fee_types_to_term(
                connection, from_year, from_term, to_year, to_term
            )
            run_id = run(
                """
                INSERT INTO term_rollover_runs (
                    academic_year, from_term, to_term, to_academic_year, status, total_students,
                    reset_students, carry_students, previous_outstanding_total, new_term_total,
                    carry_forward_total, opening_balance_total, executed_by
                )
                VALUES (%s, %s, %s, %s, 'RUNNING', %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    from_year, from_term, to_term, to_year,
                    summary['total_students'], summary['reset_students'], summary['carry_students'],
                    summary['previous_outstanding_total'], summary['new_term_total'],
                    summary['carry_forward_total'], summary['opening_balance_total'], executed_by
                )
            )

            for row in preview['rows']:
                run(
                    """
                    INSERT INTO term_rollover_run_items (
                        run_id, student_id, student_code, student_name, class_name, previous_outstanding,
                        new_term_total, carry_forward_total, reset_amount, opening_balance,
                        payment_status, carry_status, details_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id, row['student_id'], row['student_code'], row['student_name'], row['class'],
                        row['previous_outstanding'], row['new_term_total'], row['carry_forward_total'],
                        row['reset_amount'], row['opening_balance'], row['payment_status'],
                        row['carry_status'], json.dumps(row.get('details') or [])
                    )
                )

            # Replace any previously stored carry-forward rows for the target period.
            for table in ('student_term_fee_rollover_items', 'student_term_fee_rollovers'):
                run(f"DELETE FROM {table} WHERE to_academic_year = %s AND to_term = %s", (to_year, to_term))

            for row in preview['rows']:
                net_carried = 0.0
                for detail in cls._merge_carry_details(row.get('details') or []):
                    carried_amount = float(detail['carried_amount'])
                    net_carried += carried_amount
                    run(
                        """
                        INSERT INTO student_term_fee_rollover_items (
                            student_id, from_academic_year, from_term, to_academic_year, to_term,
                            source_fee_type_id, source_fee_name, source_is_required, source_is_class_specific,
                            source_expected_amount, source_paid_amount, carried_amount, source_status,
                            target_fee_type_id, target_fee_name, target_applicable, run_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            row['student_id'], from_year, from_term, to_year, to_term,
                            detail.get('fee_type_id'),
                            detail['fee_name'],
                            1 if detail.get('is_required') else 0,
                            1 if detail.get('is_class_specific') else 0,
                            float(detail.get('expected_amount') or 0),
                            float(detail.get('paid_amount') or 0),
                            carried_amount,
                            detail.get('status') or 'Carried Forward',
                            detail.get('target_fee_type_id'),
                            detail['fee_name'],
                            1 if detail.get('target_applicable') else 0,
                            run_id
                        )
                    )

                # carried_balance < 0 is a credit the student brings into the new term.
                run(
                    """
                    INSERT INTO student_term_fee_rollovers (
                        student_id, from_academic_year, from_term, to_academic_year, to_term,
                        carried_balance, source_total_due, source_total_paid
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row['student_id'], from_year, from_term, to_year, to_term,
                        round(net_carried, 2),
                        row['previous_outstanding'],
                        row['previous_outstanding'] - max(net_carried, 0.0)
                    )
                )

            run(
                """
                INSERT INTO term_changes (
                    academic_year, previous_academic_year, previous_term, term_name, start_date, rollover_processed
                )
                VALUES (%s, %s, %s, %s, %s, 1)
                """,
                (to_year, from_year, from_term, to_term, term_start_date)
            )
            try:
                from database.queries import student_is_new_available
                if student_is_new_available():
                    rows = run("SELECT COUNT(*) AS count FROM students WHERE is_new = 1", fetch=True) or []
                    continuing_students_updated = int(rows[0].get('count') or 0) if rows else 0
                    run("UPDATE students SET is_new = 0 WHERE is_new = 1")
            except Exception:
                continuing_students_updated = 0
            run(
                "UPDATE term_rollover_runs SET status = 'COMPLETED', completed_at = NOW() WHERE run_id = %s",
                (run_id,)
            )

        cls._advance_configured_period(from_year, from_term, to_year, to_term, term_start_date)

        preview['run_id'] = run_id
        preview['executed'] = True
        preview['year_changed'] = year_changes
        preview['cloned_fee_types'] = cloned_fee_types
        preview['continuing_students_updated'] = continuing_students_updated
        return preview

    @staticmethod
    def _advance_configured_period(from_year, from_term, to_year, to_term, term_start_date=None) -> None:
        """Point the configuration at the new period after a committed rollover."""
        C = config.Config
        if to_year != from_year:
            # Term/year dates still describe the old academic year. Left in place
            # they would filter the new year's payments and expenses out of every
            # term-scoped figure, so they are cleared until the new dates are set.
            cutoff = C.academic_year_date_cutoff()
            C.TERM_SCHEDULE = C.clear_stale_term_dates(C.TERM_SCHEDULE, cutoff)
            C.ACADEMIC_YEAR_START_DATE = None
            C.ACADEMIC_YEAR_END_DATE = None
            C.TERM_END_DATE = None
        C.PREVIOUS_ACADEMIC_YEAR = from_year
        C.PREVIOUS_TERM = from_term
        C.CURRENT_ACADEMIC_YEAR = to_year
        C.CURRENT_TERM = to_term
        if term_start_date:
            C.TERM_START_DATE = term_start_date
            schedule = dict(C.TERM_SCHEDULE or {})
            schedule[to_term] = {**(schedule.get(to_term) or {}), 'start_date': term_start_date}
            C.TERM_SCHEDULE = schedule
        elif to_year != from_year:
            C.TERM_START_DATE = None
        C.save_user_settings()
