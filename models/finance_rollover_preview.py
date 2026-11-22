"""Term rollover preview helpers.

Carry-forward rules applied per student when moving to the next term:

* An unpaid required fee is carried forward. An unpaid optional or class-specific
  fee is carried only if the same fee applies to the student next term;
  otherwise it is reset (written off). Manually excluded students have all of
  their debt reset.
* Balances carried *into* the closing term are reduced by payments recorded
  against the "Carried Forward Fee Balance" fee during that term.
* Overpayments (paid beyond a fee, beyond the carried balance, or a credit
  brought in from earlier) form a credit pool. The pool settles the student's
  outstanding amounts first (carried, then reset); whatever remains is carried
  into the next term as a credit (a negative carried amount).
"""
import json
from typing import List, Dict, Any
import config
from database.connection import db
from .finance_fee_types import FeeType

CREDIT_FEE_NAME = "Credit Balance"


class FinanceRolloverPreviewMixin:
    @classmethod
    def _existing_carried_rows_for_term(cls, academic_year: str, term: str) -> List[Dict[str, Any]]:
        """Return carried-forward items (debts and credits) brought into the given term."""
        cls._ensure_term_rollover_tables()
        query = """
            SELECT
                s.student_id,
                s.student_code,
                CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                s.class AS class_name,
                ri.source_fee_name,
                ri.source_is_required,
                ri.source_is_class_specific,
                COALESCE(ri.carried_amount, 0) AS carried_amount,
                ri.source_status
            FROM student_term_fee_rollover_items ri
            JOIN students s ON s.student_id = ri.student_id
            WHERE ri.to_academic_year = %s
              AND ri.to_term = %s
              AND COALESCE(ri.carried_amount, 0) <> 0
              AND s.is_active = 1
            ORDER BY s.class, s.last_name, s.first_name, ri.source_fee_name
        """
        return db.execute_query(query, (academic_year, term), fetch=True) or []

    @classmethod
    def _next_term_fee_lookup(cls, academic_year: str, term: str) -> Dict[tuple, Dict[str, Any]]:
        """Build next-term fee lookup by normalized fee name and class."""
        rows = cls._student_fee_rows_for_term(academic_year, term)
        lookup: Dict[tuple, Dict[str, Any]] = {}
        for row in rows:
            key = (int(row.get('student_id') or 0), (row.get('fee_name') or '').strip().lower())
            lookup[key] = row
        return lookup

    @staticmethod
    def _normalize_excluded_carry_student_ids(excluded_student_ids=None) -> set[int]:
        cleaned: set[int] = set()
        for value in excluded_student_ids or []:
            try:
                student_id = int(value)
            except (TypeError, ValueError):
                continue
            if student_id > 0:
                cleaned.add(student_id)
        return cleaned

    @staticmethod
    def _should_carry(is_required: bool, is_class_specific: bool, target_applicable: bool) -> bool:
        return is_required or ((not is_required or is_class_specific) and target_applicable)

    @classmethod
    def _build_term_rollover_preview(
        cls,
        from_academic_year: str,
        from_term: str,
        to_academic_year: str,
        to_term: str,
        excluded_student_ids=None
    ) -> Dict[str, Any]:
        """Build deterministic preview data for a term rollover."""
        excluded_carry_ids = cls._normalize_excluded_carry_student_ids(excluded_student_ids)
        # A new academic year moves pupils up a class: next-term fees are those of the new class.
        promote = to_academic_year != from_academic_year
        source_fee_rows = cls._student_fee_rows_for_term(from_academic_year, from_term)
        next_term_rows = cls._student_fee_rows_for_term(
            to_academic_year, to_term, treat_new_students_as_continuing=True, promote_classes=promote
        )
        existing_carry_rows = cls._existing_carried_rows_for_term(from_academic_year, from_term)
        warnings: List[str] = []
        projected_next_term_rows, inherited_templates = cls._build_projected_term_fee_rows(
            from_academic_year,
            from_term,
            to_academic_year,
            to_term,
            treat_new_students_as_continuing=True,
            promote_classes=promote,
        )
        if inherited_templates > 0:
            next_term_rows = projected_next_term_rows
            warnings.append(
                f"{inherited_templates} fee types from {from_term} {from_academic_year} will be copied "
                f"into {to_term} {to_academic_year} during rollover."
            )
        elif not next_term_rows:
            warnings.append(
                f"No fee types are configured for {to_term} in {to_academic_year}. "
                f"New term fees will remain 0 until fee types are added."
            )

        student_map: Dict[int, Dict[str, Any]] = {}

        def ensure_student(row: Dict[str, Any]) -> Dict[str, Any]:
            sid = int(row.get('student_id') or 0)
            if sid not in student_map:
                student_map[sid] = {
                    'student_id': sid,
                    'student_code': row.get('student_code') or '',
                    'student_name': row.get('student_name') or '',
                    'class': row.get('class_name') or '',
                    'previous_fee_outstanding': 0.0,
                    'existing_carried_in': 0.0,
                    'previous_outstanding': 0.0,
                    'new_term_total': 0.0,
                    'carry_forward_total': 0.0,
                    'credit_carried': 0.0,
                    'reset_amount': 0.0,
                    'opening_balance': 0.0,
                    'include_carry_forward': True,
                    'payment_status': 'Paid',
                    'carry_status': 'Reset',
                    'details': [],
                    '_credit_pool': 0.0,
                    '_carry_paid': 0.0,
                }
            return student_map[sid]

        next_lookup: Dict[tuple, Dict[str, Any]] = {}
        for row in next_term_rows:
            key = (int(row.get('student_id') or 0), (row.get('fee_name') or '').strip().lower())
            next_lookup[key] = row

        def add_debt(student, source, fee_name, fee_type_id, expected, paid, outstanding,
                     is_required, is_class_specific):
            target = next_lookup.get((student['student_id'], fee_name.strip().lower()))
            carry = cls._should_carry(is_required, is_class_specific, target is not None)
            student['details'].append({
                'source': source,
                'fee_type_id': fee_type_id,
                'fee_name': fee_name,
                'expected_amount': expected,
                'paid_amount': paid,
                'outstanding': outstanding,
                'is_required': is_required,
                'is_class_specific': is_class_specific,
                'target_fee_type_id': target.get('fee_type_id') if target else None,
                'target_applicable': target is not None,
                'carried_amount': outstanding if carry else 0.0,
                'reset_amount': 0.0 if carry else outstanding,
                'credit_applied': 0.0,
                'status': 'Carried Forward' if carry else 'Reset',
            })

        # 1. Fees of the closing term.
        for row in source_fee_rows:
            student = ensure_student(row)
            fee_name = row.get('fee_name') or ''
            expected = float(row.get('expected_amount') or 0)
            paid = float(row.get('paid_amount') or 0)
            if FeeType.is_carried_forward_fee_name(fee_name):
                # Payments that settle the balance brought into this term.
                student['_carry_paid'] += paid
                continue
            if paid > expected:
                student['_credit_pool'] += paid - expected
            outstanding = max(expected - paid, 0.0)
            if outstanding <= 0:
                continue
            student['previous_fee_outstanding'] += outstanding
            add_debt(student, 'previous_term_fee', fee_name, row.get('fee_type_id'), expected, paid,
                     outstanding, bool(row.get('is_required')), bool(row.get('is_class_specific')))

        # 2. Balances brought into the closing term, less what was paid against them.
        for row in existing_carry_rows:
            student = ensure_student(row)
            amount = float(row.get('carried_amount') or 0)
            if amount < 0:
                student['_credit_pool'] += -amount       # credit brought in, still unused
                continue
            settled = min(student['_carry_paid'], amount)
            student['_carry_paid'] -= settled
            outstanding = amount - settled
            student['existing_carried_in'] += outstanding
            if outstanding <= 0:
                continue
            add_debt(student, 'prior_carry', row.get('source_fee_name') or 'Carried Balance', None,
                     amount, settled, outstanding,
                     bool(row.get('source_is_required')), bool(row.get('source_is_class_specific')))

        for row in next_term_rows:
            student = ensure_student(row)
            student['new_term_total'] += float(row.get('expected_amount') or 0)

        preview_rows = []
        for student in student_map.values():
            details = student['details']
            # Paid against the carried balance beyond what was owed: an overpayment.
            student['_credit_pool'] += max(student.pop('_carry_paid'), 0.0)
            credit_pool = student.pop('_credit_pool')

            student['include_carry_forward'] = student['student_id'] not in excluded_carry_ids
            if not student['include_carry_forward']:
                for detail in details:
                    if detail['carried_amount'] > 0:
                        detail['reset_amount'] += detail['carried_amount']
                        detail['carried_amount'] = 0.0
                        detail['status'] = 'Reset'
                        detail['carry_excluded'] = True

            # Overpayments settle what the student still owes: carried debt first,
            # then amounts that would otherwise be written off.
            for field in ('carried_amount', 'reset_amount'):
                for detail in details:
                    if credit_pool <= 0:
                        break
                    use = min(credit_pool, detail[field])
                    if use > 0:
                        detail[field] -= use
                        detail['credit_applied'] += use
                        credit_pool -= use
                        if detail['carried_amount'] <= 0 and detail['reset_amount'] <= 0:
                            detail['status'] = 'Settled by Credit'

            if credit_pool > 0:
                details.append({
                    'source': 'credit',
                    'fee_type_id': None,
                    'fee_name': CREDIT_FEE_NAME,
                    'expected_amount': 0.0,
                    'paid_amount': credit_pool,
                    'outstanding': -credit_pool,
                    'is_required': True,
                    'is_class_specific': False,
                    'target_fee_type_id': None,
                    'target_applicable': True,
                    'carried_amount': -credit_pool,
                    'reset_amount': 0.0,
                    'credit_applied': 0.0,
                    'status': 'Credit Forward',  # source_status is VARCHAR(20)
                })

            student['reset_amount'] = sum(d['reset_amount'] for d in details)
            net_carry = sum(d['carried_amount'] for d in details)
            student['carry_forward_total'] = net_carry
            student['credit_carried'] = credit_pool if credit_pool > 0 else 0.0
            student['previous_outstanding'] = student['previous_fee_outstanding'] + student['existing_carried_in']
            student['opening_balance'] = student['new_term_total'] + net_carry
            if student['previous_outstanding'] <= 0:
                student['payment_status'] = 'Paid'
            elif student['previous_outstanding'] < student['new_term_total'] + max(net_carry, 0.0):
                student['payment_status'] = 'Partial'
            else:
                student['payment_status'] = 'Unpaid'
            if net_carry > 0:
                student['carry_status'] = 'Carried Forward'
            elif net_carry < 0:
                student['carry_status'] = 'Credit'
            else:
                student['carry_status'] = 'Reset'
            preview_rows.append(student)

        promotion = cls.get_promotion_plan() if promote else None
        if promotion:
            graduating = set(promotion['graduating_student_ids'])
            for row in preview_rows:
                row['next_class'] = config.Config.promoted_class(row.get('class'))
                row['graduating'] = row['student_id'] in graduating
            leaving_owing = [r for r in preview_rows if r['graduating'] and r['carry_forward_total'] > 0]
            promotion['graduating_with_balance'] = len(leaving_owing)
            promotion['graduating_balance_total'] = round(sum(r['carry_forward_total'] for r in leaving_owing), 2)
            if leaving_owing:
                warnings.append(
                    f"{len(leaving_owing)} graduating pupil(s) still owe a total of "
                    f"{promotion['graduating_balance_total']:,.2f}; the balance stays on their (inactive) record."
                )

        preview_rows.sort(key=lambda r: (r.get('class') or '', r.get('student_name') or ''))
        summary = {
            'total_students': len(preview_rows),
            'reset_students': sum(1 for r in preview_rows if r['carry_forward_total'] == 0),
            'carry_students': sum(1 for r in preview_rows if r['carry_forward_total'] > 0),
            'credit_students': sum(1 for r in preview_rows if r['carry_forward_total'] < 0),
            'previous_outstanding_total': round(sum(r['previous_outstanding'] for r in preview_rows), 2),
            'new_term_total': round(sum(r['new_term_total'] for r in preview_rows), 2),
            'carry_forward_total': round(sum(max(r['carry_forward_total'], 0.0) for r in preview_rows), 2),
            'credit_carried_total': round(sum(r['credit_carried'] for r in preview_rows), 2),
            'opening_balance_total': round(sum(r['opening_balance'] for r in preview_rows), 2),
        }
        return {
            'academic_year': from_academic_year,          # kept for existing callers
            'from_academic_year': from_academic_year,
            'to_academic_year': to_academic_year,
            'from_term': from_term,
            'to_term': to_term,
            'rows': preview_rows,
            'summary': summary,
            'warnings': warnings,
            'projected_fee_type_copies': inherited_templates,
            'promotion': promotion,                       # None unless the academic year changes
            'excluded_carry_student_ids': sorted(excluded_carry_ids)
        }

    @classmethod
    def get_term_rollover_preview(
        cls,
        academic_year: str = None,
        from_term: str = None,
        to_term: str = None,
        excluded_student_ids=None,
        to_academic_year: str = None,
    ) -> Dict[str, Any]:
        """Return rollover preview and persist a preview snapshot record.

        `academic_year`/`from_term` identify the closing period (defaults: the
        current one). The target is always the next period; `to_term` and
        `to_academic_year` are optional and only validated.
        """
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        from_term = config.Config.normalize_term_name(from_term or config.Config.CURRENT_TERM)
        to_academic_year, to_term = cls._resolve_rollover_target(
            academic_year, from_term, to_term, to_academic_year
        )
        cls._ensure_rollover_year_columns()

        preview = cls._build_term_rollover_preview(
            academic_year, from_term, to_academic_year, to_term, excluded_student_ids=excluded_student_ids
        )
        summary = preview['summary']
        executed_by = getattr(config.Config, 'CURRENT_USER', None) or 'System'
        run_id = db.execute_query(
            """
            INSERT INTO term_rollover_runs (
                academic_year, from_term, to_term, to_academic_year, status, total_students, reset_students,
                carry_students, previous_outstanding_total, new_term_total, carry_forward_total,
                opening_balance_total, executed_by
            )
            VALUES (%s, %s, %s, %s, 'PREVIEW', %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                academic_year,
                from_term,
                to_term,
                to_academic_year,
                summary['total_students'],
                summary['reset_students'],
                summary['carry_students'],
                summary['previous_outstanding_total'],
                summary['new_term_total'],
                summary['carry_forward_total'],
                summary['opening_balance_total'],
                executed_by
            )
        )
        preview['run_id'] = run_id

        item_params = [
            (
                run_id,
                row['student_id'],
                row['student_code'],
                row['student_name'],
                row['class'],
                row['previous_outstanding'],
                row['new_term_total'],
                row['carry_forward_total'],
                row['reset_amount'],
                row['opening_balance'],
                row['payment_status'],
                row['carry_status'],
                json.dumps(row.get('details') or [])
            )
            for row in preview['rows']
        ]
        if item_params:
            db.execute_many(
                """
                INSERT INTO term_rollover_run_items (
                    run_id, student_id, student_code, student_name, class_name, previous_outstanding,
                    new_term_total, carry_forward_total, reset_amount, opening_balance,
                    payment_status, carry_status, details_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                item_params
            )
        return preview
