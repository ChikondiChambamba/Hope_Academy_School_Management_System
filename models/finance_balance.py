"""Central student balance allocation logic for finance."""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import config
from database.connection import db
from .finance_fee_types import FeeType



# (backend, year, fee type, term, term dates) -> (write generation, rows)
_BALANCE_CACHE: Dict[tuple, tuple] = {}


class FinanceBalanceMixin:
    @staticmethod
    def _parse_term_schedule_date(value: Any) -> Optional[date]:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if not value:
            return None
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except Exception:
            return None

    @staticmethod
    def _get_term_payment_allocations(academic_year: str, term: str) -> Dict[int, Dict[str, float]]:
        """Return term payments split into carried-forward and normal fee buckets."""
        term = config.Config.normalize_term_name(term)
        FeeType.ensure_carried_forward_fee_type(academic_year, term)
        start_raw, end_raw = config.Config.get_term_date_range(term)
        start_date = FinanceBalanceMixin._parse_term_schedule_date(start_raw)
        end_date = FinanceBalanceMixin._parse_term_schedule_date(end_raw)

        params: List[Any] = [academic_year]
        filters = ["ft.academic_year = %s"]
        if start_date:
            filters.append("sf.payment_date >= %s")
            params.append(start_date)
        if end_date:
            filters.append("sf.payment_date <= %s")
            params.append(end_date)
        if not start_date and not end_date:
            aliases = config.Config.get_term_aliases(term) or [term]
            placeholders = ", ".join(["%s"] * len(aliases))
            filters.append(
                f"""(
                    ft.term IN ({placeholders})
                    OR ft.term IS NULL
                    OR ft.term = ''
                    OR NOT EXISTS (
                        SELECT 1 FROM fee_types ftx
                        WHERE ftx.academic_year = %s AND ftx.term IN ({placeholders})
                    )
                )"""
            )
            params.extend(aliases)
            params.append(academic_year)
            params.extend(aliases)

        rows = db.execute_query(
            f"""
            SELECT
                sf.student_id,
                COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
                COALESCE(SUM(CASE WHEN LOWER(TRIM(ft.fee_name)) = LOWER(%s) THEN sf.amount_paid ELSE 0 END), 0) AS carried_paid,
                COALESCE(SUM(CASE WHEN LOWER(TRIM(ft.fee_name)) = LOWER(%s) THEN 0 ELSE sf.amount_paid END), 0) AS current_paid
            FROM student_fees sf
            JOIN fee_types ft ON ft.fee_type_id = sf.fee_type_id
            WHERE {' AND '.join(filters)}
            GROUP BY sf.student_id
            """,
            tuple([FeeType.CARRIED_FORWARD_FEE_NAME, FeeType.CARRIED_FORWARD_FEE_NAME] + params),
            fetch=True
        ) or []
        return {
            int(row['student_id']): {
                'total_paid': float(row.get('total_paid') or 0),
                'carried_paid': float(row.get('carried_paid') or 0),
                'current_paid': float(row.get('current_paid') or 0),
            }
            for row in rows
            if row.get('student_id') is not None
        }

    @classmethod
    def _get_term_payment_totals(cls, academic_year: str, term: str) -> Dict[int, float]:
        allocations = cls._get_term_payment_allocations(academic_year, term)
        return {sid: values['total_paid'] for sid, values in allocations.items()}

    @staticmethod
    def _allocate_opening_balance(
        total_current_fees: float,
        total_paid: float,
        opening_carried_balance: float,
        carried_paid: float = None,
        current_paid: float = None
    ) -> Dict[str, float]:
        """Split a term's payments between the carried balance and current fees.

        Rules (no money is ever dropped):
          * `opening_carried_balance` > 0 is debt brought forward; < 0 is a credit
            brought forward, which reduces this term's fees.
          * Payments recorded against the carried-forward fee (`carried_paid`)
            settle the carried debt first; with no split given, all payments do.
            Any excess flows on to the current term's fees.
          * Whatever is paid beyond the total owed is an overpayment: `balance`
            goes negative and that credit is carried into the next term.
        Invariant: balance == opening_carried_balance + total_current_fees - total_paid.
        """
        fees = float(total_current_fees or 0)
        carried = float(opening_carried_balance or 0)
        if carried_paid is None and current_paid is None:
            paid = float(total_paid or 0)
            paid_against_carry = paid
        else:
            paid_against_carry = float(carried_paid or 0)
            paid = paid_against_carry + float(current_paid or 0)

        carried_debt = max(carried, 0.0)
        credit_brought_forward = max(-carried, 0.0)
        paid_to_carried_balance = min(max(paid_against_carry, 0.0), carried_debt)
        remaining_carried_balance = carried_debt - paid_to_carried_balance
        paid_to_current_fees = paid - paid_to_carried_balance
        current_term_balance = fees - credit_brought_forward - paid_to_current_fees
        opening_balance = carried + fees
        balance = remaining_carried_balance + current_term_balance
        return {
            'opening_balance': opening_balance,
            'opening_due': opening_balance,
            'opening_carried_balance': carried,
            'original_carried_balance': carried,
            'credit_brought_forward': credit_brought_forward,
            'paid_to_carried_balance': paid_to_carried_balance,
            'remaining_carried_balance': remaining_carried_balance,
            'paid_to_current_fees': paid_to_current_fees,
            'paid_applied_to_current_fees': min(max(fees - credit_brought_forward, 0.0), max(paid_to_current_fees, 0.0)),
            'current_term_balance': current_term_balance,
            'effective_total_paid': min(paid, max(opening_balance, 0.0)),
            'overpayment': max(-balance, 0.0),
            'balance': balance,
        }

    @classmethod
    def get_student_balances(cls, academic_year: str = None, fee_type_id: int = None, term: str = None) -> List[Dict]:
        """Central source for all student fee balances.

        Screens ask for the same balances several times while loading; the result
        is reused until any data changes (db.write_generation), so it is never stale.
        """
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        term = config.Config.normalize_term_name(term or config.Config.CURRENT_TERM)
        generation = getattr(db, 'write_generation', None)
        if not isinstance(generation, int):          # e.g. a test double: no caching
            return cls._compute_student_balances(academic_year, fee_type_id, term)
        key = (id(db.backend), academic_year, fee_type_id, term, tuple(config.Config.get_term_date_range(term)))
        cached = _BALANCE_CACHE.get(key)
        if cached and cached[0] == generation:
            return [dict(row) for row in cached[1]]
        rows = cls._compute_student_balances(academic_year, fee_type_id, term)
        if rows:   # an empty result may come from an error; do not keep it
            if len(_BALANCE_CACHE) > 32:
                _BALANCE_CACHE.clear()
            _BALANCE_CACHE[key] = (db.write_generation, [dict(row) for row in rows])
        return rows

    @classmethod
    def _compute_student_balances(cls, academic_year: str, fee_type_id: int, term: str) -> List[Dict]:
        try:
            cls._ensure_term_rollover_tables()
            FeeType.ensure_term_labels()
            carried_fee_type_id = FeeType.ensure_carried_forward_fee_type(academic_year, term)
            selected_is_carried = bool(fee_type_id and carried_fee_type_id and int(fee_type_id) == int(carried_fee_type_id))
            from database.queries import student_is_new_available
            aliases = config.Config.get_term_aliases(term) or [term]
            placeholders = ", ".join(["%s"] * len(aliases))
            is_new_guard = "AND s.is_new = 0" if student_is_new_available() else "AND 1=0"
            fee_filter = "AND ft.fee_type_id = %s" if fee_type_id else ""
            term_filter = "" if fee_type_id else f"""
                  AND (
                        ft.term IN ({placeholders})
                        OR ft.term IS NULL
                        OR ft.term = ''
                        OR NOT EXISTS (
                            SELECT 1 FROM fee_types ftx
                            WHERE ftx.academic_year = %s AND ftx.term IN ({placeholders})
                        )
                  )
            """
            rows = db.execute_query(
                f"""
                SELECT s.student_id, s.student_code, CONCAT(s.first_name, ' ', s.last_name) AS student_name, s.class,
                       COALESCE(SUM(CASE
                           WHEN sfe.exemption_id IS NOT NULL THEN 0
                           WHEN LOWER(TRIM(ft.fee_name)) = LOWER(%s) THEN 0
                           WHEN ft.new_students_only = 1 {is_new_guard} THEN 0
                           ELSE ft.amount END), 0) AS total_fees,
                       COALESCE(SUM(sf.amount_paid), 0) AS amount_paid,
                       COALESCE(cr.carried_balance, 0) AS carried_balance
                FROM students s
                CROSS JOIN fee_types ft
                LEFT JOIN student_fee_exemptions sfe ON sfe.student_id = s.student_id AND sfe.fee_type_id = ft.fee_type_id
                LEFT JOIN (
                    SELECT student_id, fee_type_id, COALESCE(SUM(amount_paid), 0) AS amount_paid
                    FROM student_fees GROUP BY student_id, fee_type_id
                ) sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                LEFT JOIN (
                    SELECT student_id, COALESCE(SUM(carried_balance), 0) AS carried_balance
                    FROM student_term_fee_rollovers
                    WHERE to_academic_year = %s AND to_term = %s
                    GROUP BY student_id
                ) cr ON cr.student_id = s.student_id
                WHERE s.is_active = 1 AND ft.academic_year = %s
                  {term_filter}
                  AND (
                    NOT EXISTS (SELECT 1 FROM fee_type_classes ftc0 WHERE ftc0.fee_type_id = ft.fee_type_id)
                    OR EXISTS (
                        SELECT 1 FROM fee_type_classes ftc
                        JOIN classes c ON c.class_id = ftc.class_id
                        WHERE ftc.fee_type_id = ft.fee_type_id
                          AND LOWER(c.class_name) = LOWER(s.class)
                          AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                    )
                  )
                  {fee_filter}
                GROUP BY s.student_id, s.student_code, s.first_name, s.last_name, s.class, cr.carried_balance
                ORDER BY s.class, s.last_name, s.first_name
                """,
                tuple(
                    [FeeType.CARRIED_FORWARD_FEE_NAME, academic_year, term, academic_year]
                    + ([] if fee_type_id else aliases + [academic_year] + aliases)
                    + [academic_year]
                    + ([fee_type_id] if fee_type_id else [])
                ),
                fetch=True
            ) or []
            payment_allocations = cls._get_term_payment_allocations(academic_year, term)
            out = []
            for row in rows:
                sid = int(row.get('student_id') or 0)
                total_fees = float(row.get('total_fees') or 0)
                opening_carry = float(row.get('carried_balance') or 0)
                raw_fee_paid = float(row.get('amount_paid') or 0)
                paid = payment_allocations.get(sid, {'total_paid': 0.0, 'carried_paid': 0.0, 'current_paid': 0.0})
                if fee_type_id:
                    if selected_is_carried:
                        total_fees = 0.0
                        carried_paid = float(paid['carried_paid'])
                        current_paid = 0.0
                        total_paid = carried_paid
                    else:
                        opening_carry = 0.0
                        carried_paid = 0.0
                        current_paid = raw_fee_paid
                        total_paid = current_paid
                else:
                    carried_paid = float(paid['carried_paid'])
                    current_paid = float(paid['current_paid'])
                    total_paid = float(paid['total_paid'])
                allocation = cls._allocate_opening_balance(total_fees, total_paid, opening_carry, carried_paid, current_paid)
                out.append({
                    'student_id': sid,
                    'student_code': row.get('student_code'),
                    'student_name': row.get('student_name'),
                    'class': row.get('class'),
                    'total_due': total_fees,
                    'current_term_due': total_fees,
                    'total_fees': total_fees,
                    'total_paid': total_paid,
                    'amount_paid': total_paid,
                    'raw_fee_type_paid': raw_fee_paid,
                    'carried_balance': allocation['remaining_carried_balance'],
                    'remaining_carried_balance': allocation['remaining_carried_balance'],
                    'opening_carried_balance': allocation['opening_carried_balance'],
                    'original_carried_balance': allocation['opening_carried_balance'],
                    'paid_to_carried_balance': allocation['paid_to_carried_balance'],
                    'paid_to_current_fees': allocation['paid_to_current_fees'],
                    'paid_applied_to_current_fees': allocation['paid_applied_to_current_fees'],
                    'current_term_balance': allocation['current_term_balance'],
                    'opening_balance': allocation['opening_balance'],
                    'opening_due': allocation['opening_due'],
                    'effective_total_paid': allocation['effective_total_paid'],
                    'overpayment': allocation['overpayment'],
                    'balance': allocation['balance'],
                })
            return out
        except Exception:
            return []

    @classmethod
    def get_student_balance(cls, student_id: int, academic_year: str = None, fee_type_id: int = None, term: str = None) -> Dict:
        rows = cls.get_student_balances(academic_year, fee_type_id, term)
        row = next((item for item in rows if int(item.get('student_id') or 0) == int(student_id)), None)
        if row:
            return {'student_id': student_id, 'total_expected': float(row.get('total_due') or 0), **row}
        return {
            'student_id': student_id,
            'total_expected': 0,
            'total_paid': 0,
            'carried_balance': 0,
            'remaining_carried_balance': 0,
            'opening_carried_balance': 0,
            'paid_to_carried_balance': 0,
            'paid_to_current_fees': 0,
            'paid_applied_to_current_fees': 0,
            'opening_balance': 0,
            'opening_due': 0,
            'effective_total_paid': 0,
            'overpayment': 0,
            'balance': 0,
        }

    @classmethod
    def get_student_financial_snapshot(cls, student_id: int, academic_year: str = None, term: str = None) -> Dict:
        """Central source for the student preview finance summary and fee rows."""
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        term = config.Config.normalize_term_name(term or config.Config.CURRENT_TERM)
        try:
            student_rows = db.execute_query(
                """
                SELECT student_id, student_code, first_name, last_name, class, is_new
                FROM students
                WHERE student_id = %s
                """,
                (student_id,),
                fetch=True
            ) or []
            if not student_rows:
                return {}
            student = student_rows[0]
            student_class = (student.get('class') or '').strip()
            is_new = bool(student.get('is_new'))
            carry_fee_type_id = FeeType.ensure_carried_forward_fee_type(academic_year, term)
            balance_info = cls.get_student_balance(student_id, academic_year=academic_year, term=term)

            aliases = config.Config.get_term_aliases(term) or [term]
            placeholders = ", ".join(["%s"] * len(aliases))
            rows = db.execute_query(
                f"""
                SELECT ft.fee_type_id, ft.fee_name, ft.amount, ft.new_students_only,
                       CASE WHEN sfe.exemption_id IS NOT NULL THEN 1 ELSE 0 END AS is_exempt,
                       COALESCE(sf.amount_paid, 0) AS paid_amount
                FROM fee_types ft
                LEFT JOIN student_fee_exemptions sfe
                  ON sfe.student_id = %s AND sfe.fee_type_id = ft.fee_type_id
                LEFT JOIN (
                    SELECT fee_type_id, COALESCE(SUM(amount_paid), 0) AS amount_paid
                    FROM student_fees
                    WHERE student_id = %s
                    GROUP BY fee_type_id
                ) sf ON sf.fee_type_id = ft.fee_type_id
                WHERE ft.academic_year = %s
                  AND ft.term IN ({placeholders})
                  AND (
                    NOT EXISTS (SELECT 1 FROM fee_type_classes ftc0 WHERE ftc0.fee_type_id = ft.fee_type_id)
                    OR EXISTS (
                        SELECT 1 FROM fee_type_classes ftc
                        JOIN classes c ON c.class_id = ftc.class_id
                        WHERE ftc.fee_type_id = ft.fee_type_id
                          AND LOWER(c.class_name) = LOWER(%s)
                          AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                    )
                  )
                ORDER BY ft.fee_name
                """,
                tuple([student_id, student_id, academic_year] + aliases + [student_class, academic_year]),
                fetch=True
            ) or []

            fee_details = []
            current_fee_ids = set()
            for row in rows:
                fid = int(row.get('fee_type_id') or 0)
                fee_name = row.get('fee_name') or ''
                if carry_fee_type_id and fid == int(carry_fee_type_id):
                    continue
                current_fee_ids.add(fid)
                if row.get('is_exempt'):
                    expected = 0.0
                elif row.get('new_students_only') and not is_new:
                    expected = 0.0
                else:
                    expected = float(row.get('amount') or 0)
                paid = float(row.get('paid_amount') or 0)
                fee_details.append({
                    'fee_type_id': fid,
                    'fee_name': fee_name,
                    'expected_amount': expected,
                    'paid_amount': paid,
                    'balance': expected - paid
                })

            opening_carry = float(balance_info.get('opening_carried_balance') or 0)
            remaining_carry = float(balance_info.get('remaining_carried_balance') or 0)
            paid_to_carry = float(balance_info.get('paid_to_carried_balance') or 0)
            if opening_carry > 0 or paid_to_carry > 0:
                fee_details.append({
                    'fee_type_id': carry_fee_type_id,
                    'fee_name': FeeType.CARRIED_FORWARD_FEE_NAME,
                    'expected_amount': opening_carry,
                    'paid_amount': paid_to_carry,
                    'balance': remaining_carry
                })
            elif opening_carry < 0:
                # Overpayment from the previous term, applied against this term's fees.
                fee_details.append({
                    'fee_type_id': carry_fee_type_id,
                    'fee_name': 'Credit Brought Forward',
                    'expected_amount': opening_carry,
                    'paid_amount': 0.0,
                    'balance': opening_carry
                })

            payment_history = cls.get_student_payment_history(student_id)
            paid_fee_type_ids = {int(p.get('fee_type_id')) for p in payment_history if p.get('fee_type_id') is not None}
            missing_ids = [fid for fid in paid_fee_type_ids if fid not in current_fee_ids and fid != carry_fee_type_id]
            if missing_ids:
                placeholders = ", ".join(["%s"] * len(missing_ids))
                names = db.execute_query(
                    f"SELECT fee_type_id, fee_name FROM fee_types WHERE fee_type_id IN ({placeholders})",
                    tuple(missing_ids),
                    fetch=True
                ) or []
                name_map = {int(r['fee_type_id']): r.get('fee_name') for r in names}
                for fid in missing_ids:
                    paid_sum = sum(float(p.get('amount_paid') or 0) for p in payment_history if int(p.get('fee_type_id') or 0) == fid)
                    fee_details.append({
                        'fee_type_id': fid,
                        'fee_name': f"{name_map.get(fid) or f'Fee {fid}'} (Other Term)",
                        'expected_amount': paid_sum,
                        'paid_amount': paid_sum,
                        'balance': 0.0,
                        'informational_only': True
                    })

            return {
                'student_name': f"{student.get('first_name') or ''} {student.get('last_name') or ''}".strip(),
                'student_code': student.get('student_code') or '',
                'class': student_class,
                'total_due': float(balance_info.get('opening_balance') or 0),
                'total_paid': float(balance_info.get('effective_total_paid') or 0),
                'balance': float(balance_info.get('balance') or 0),
                'carried_balance': remaining_carry,
                'remaining_carried_balance': remaining_carry,
                'opening_carried_balance': opening_carry,
                'paid_to_carried_balance': paid_to_carry,
                'fee_details': fee_details,
                'payment_history': payment_history
            }
        except Exception:
            return {}

    @staticmethod
    def get_student_payment_history(student_id: int) -> List[Dict]:
        """Return fresh payment history for student finance preview."""
        try:
            return db.execute_query(
                """
                SELECT sf.payment_date, sf.fee_type_id, ft.fee_name, sf.amount_paid,
                       sf.payment_method, sf.receipt_number
                FROM student_fees sf
                JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
                WHERE sf.student_id = %s
                ORDER BY sf.payment_date DESC, sf.created_at DESC, sf.fee_id DESC
                """,
                (student_id,),
                fetch=True
            ) or []
        except Exception:
            return []
