"""Fee payment model and collection queries."""
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import config
from database.connection import db
from database.queries import Queries
from .finance_fee_types import FeeType

@dataclass
class FeePayment:
    """Fee payment model"""
    
    fee_id: Optional[int] = None
    student_id: int = 0
    fee_type_id: int = 0
    amount_paid: float = 0.0
    payment_date: Optional[date] = None
    payment_method: str = "Cash"
    receipt_number: str = ""
    description: str = ""
    created_at: Optional[datetime] = None
    
    # Joined fields
    student_name: str = ""
    fee_name: str = ""
    
    def __post_init__(self):
        """Initialize after dataclass creation"""
        if isinstance(self.payment_date, str):
            self.payment_date = datetime.strptime(self.payment_date, '%Y-%m-%d').date()
        if not self.payment_date:
            self.payment_date = date.today()
    
    def validate(self) -> tuple[bool, str]:
        """Validate fee payment data"""
        if self.student_id <= 0:
            return False, "Student ID is required"
        
        if self.fee_type_id <= 0:
            return False, "Fee type is required"
        
        if self.amount_paid <= 0:
            return False, "Amount must be greater than 0"
        
        if not self.payment_date:
            return False, "Payment date is required"
        
        if self.payment_date > date.today():
            return False, "Payment date cannot be in the future"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save fee payment to database"""
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        # Attempt insert with retries to handle rare receipt-number collisions
        attempts = 0
        max_attempts = 5
        while attempts < max_attempts:
            try:
                from utils.audit_logger import log_payment_action
                
                # Generate receipt number if not provided
                if not self.receipt_number:
                    self.receipt_number = self.generate_receipt_number()

                query = """
                    INSERT INTO student_fees 
                    (student_id, fee_type_id, amount_paid, payment_date, 
                     payment_method, receipt_number, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    self.student_id,
                    self.fee_type_id,
                    self.amount_paid,
                    self.payment_date,
                    self.payment_method,
                    self.receipt_number,
                    self.description
                )

                self.fee_id = db.execute_query(query, params)
                
                # Log the payment action
                log_payment_action('CREATE', self.fee_id, 
                                 f'Payment of {self.amount_paid} recorded for student {self.student_id}',
                                 {'receipt_number': self.receipt_number, 'method': self.payment_method})

                # No automatic exemptions here. An earlier rule exempted the pupil from every
                # other fee named "tuition" in the academic year whenever one was paid, which
                # also cancelled other terms' tuition. Class-specific fees already prevent
                # double charging; exemptions are only ever added deliberately.

                return True, f"Payment recorded successfully. Receipt: {self.receipt_number}"

            except Exception as e:
                msg = str(e)
                # If the error is a duplicate-receipt collision, regenerate and retry
                if 'Duplicate entry' in msg and 'receipt_number' in msg and attempts < max_attempts - 1:
                    attempts += 1
                    # create a new receipt and try again
                    self.receipt_number = self.generate_receipt_number()
                    continue
                
                # Log the failed action
                from utils.audit_logger import log_payment_action
                log_payment_action('CREATE', 0, f'Payment failed: {msg}', None, 'FAILED')
                
                return False, f"Database error: {msg}"

        return False, "Database error: failed to generate unique receipt after retries"

    def update(self) -> tuple[bool, str]:
        """Update an existing fee payment record"""
        # Ensure we have an id
        if not self.fee_id:
            return False, "Payment ID is missing for update"

        is_valid, message = self.validate()
        if not is_valid:
            return False, message

        try:
            query = """
                UPDATE student_fees SET
                  student_id = %s,
                  fee_type_id = %s,
                  amount_paid = %s,
                  payment_date = %s,
                  payment_method = %s,
                  receipt_number = %s,
                  description = %s
                WHERE fee_id = %s
            """
            params = (
                self.student_id,
                self.fee_type_id,
                self.amount_paid,
                self.payment_date,
                self.payment_method,
                self.receipt_number,
                self.description,
                self.fee_id
            )
            db.execute_query(query, params)
            return True, "Payment updated successfully"
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def generate_receipt_number(self) -> str:
        """Generate unique receipt number"""
        try:
            # Format: REC-YYYYMMDD-XXXX
            date_str = datetime.now().strftime('%Y%m%d')

            # Use a DB-backed daily sequence to avoid race conditions:
            # insert today's row, or atomically increment it if it exists.
            try:
                upsert = (
                    "INSERT INTO receipt_sequence (seq_date, seq) VALUES (%s, 1) "
                    + db.upsert_clause(("seq_date",), set_sql={"seq": "seq + 1"})
                )
                db.execute_query(upsert, (date_str,))

                # Now fetch the current seq value for today
                res = db.execute_query("SELECT seq FROM receipt_sequence WHERE seq_date = %s", (date_str,), fetch=True)
                if res and len(res) > 0 and 'seq' in res[0]:
                    seq = int(res[0]['seq'])
                    return f"REC-{date_str}-{seq:04d}"
            except Exception:
                # Fall back to the previous safe method below if anything goes wrong
                pass
        except:
            # Fallback
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            return f"REC-{timestamp}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert fee payment to dictionary"""
        data = asdict(self)
        
        # Convert dates to strings
        if data['payment_date'] and isinstance(data['payment_date'], date):
            data['payment_date'] = data['payment_date'].isoformat()
        
        # Convert datetime to string
        if data['created_at'] and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FeePayment':
        """Create FeePayment instance from a query row (extra joined columns are ignored)."""
        from .row_mapping import from_row
        return from_row(cls, data)
    
    @classmethod
    def get_by_date_range(cls, start_date: date, end_date: date) -> List['FeePayment']:
        """Get fee payments within date range"""
        try:
            query = Queries.GET_FEE_PAYMENTS_BY_DATE
            results = db.execute_query(query, (start_date, end_date), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_student(cls, student_id: int) -> List['FeePayment']:
        """Get all payments for a student"""
        try:
            query = """
                SELECT 
                    sf.*,
                    s.first_name,
                    s.last_name,
                    ft.fee_name
                FROM student_fees sf
                JOIN students s ON sf.student_id = s.student_id
                JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
                WHERE sf.student_id = %s
                ORDER BY sf.payment_date DESC
            """
            results = db.execute_query(query, (student_id,), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_total_collected(cls, start_date: date = None, end_date: date = None) -> Dict:
        """Get total fees collected for period"""
        try:
            if not start_date:
                start_date = date(date.today().year, 1, 1)
            if not end_date:
                end_date = date.today()
            
            query = Queries.GET_TOTAL_FEES_COLLECTED
            results = db.execute_query(query, (start_date, end_date), fetch=True)
            
            total = sum(r['total_amount'] for r in results)
            count = sum(r['payment_count'] for r in results)
            
            return {
                'total_amount': total,
                'payment_count': count,
                'monthly_breakdown': results
            }
        except:
            return {'total_amount': 0, 'payment_count': 0, 'monthly_breakdown': []}

    @classmethod
    def get_collected_by_fee_type(cls, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """Get total collected grouped by fee type for a period"""
        try:
            if not start_date:
                start_date = date(date.today().year, 1, 1)
            if not end_date:
                end_date = date.today()

            query = """
                SELECT ft.fee_type_id, ft.fee_name, COALESCE(SUM(sf.amount_paid), 0) AS total_collected,
                       COUNT(sf.fee_id) AS payment_count
                FROM fee_types ft
                LEFT JOIN student_fees sf ON ft.fee_type_id = sf.fee_type_id AND sf.payment_date BETWEEN %s AND %s
                WHERE ft.academic_year = %s
                GROUP BY ft.fee_type_id, ft.fee_name
                ORDER BY total_collected DESC
            """
            results = db.execute_query(query, (start_date, end_date, config.Config.CURRENT_ACADEMIC_YEAR), fetch=True)
            return results
        except:
            return []

    @classmethod
    def get_total_collected_for_term(cls, academic_year: str = None, term: str = None) -> Dict[str, Any]:
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        term = config.Config.normalize_term_name(term or config.Config.CURRENT_TERM)
        start_raw, end_raw = config.Config.get_term_date_range(term)
        start_date = datetime.strptime(start_raw, "%Y-%m-%d").date() if start_raw else None
        end_date = datetime.strptime(end_raw, "%Y-%m-%d").date() if end_raw else None
        params = [academic_year]
        filters = ["ft.academic_year = %s"]
        if start_date:
            filters.append("sf.payment_date >= %s")
            params.append(start_date)
        if end_date:
            filters.append("sf.payment_date <= %s")
            params.append(end_date)
        rows = db.execute_query(
            f"""
            SELECT DATE_FORMAT(sf.payment_date, '%Y-%m') AS month,
                   COALESCE(SUM(sf.amount_paid), 0) AS total_amount,
                   COUNT(sf.fee_id) AS payment_count
            FROM student_fees sf
            JOIN fee_types ft ON ft.fee_type_id = sf.fee_type_id
            WHERE {' AND '.join(filters)}
            GROUP BY DATE_FORMAT(sf.payment_date, '%Y-%m')
            ORDER BY month
            """,
            tuple(params),
            fetch=True
        ) or []
        return {
            'total_amount': sum(float(r.get('total_amount') or 0) for r in rows),
            'payment_count': sum(int(r.get('payment_count') or 0) for r in rows),
            'monthly_breakdown': rows
        }

    @classmethod
    def get_total_collected_for_academic_year(cls, academic_year: str = None) -> Dict[str, Any]:
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        rows = db.execute_query(
            """
            SELECT COALESCE(SUM(sf.amount_paid), 0) AS total_amount, COUNT(sf.fee_id) AS payment_count
            FROM student_fees sf
            JOIN fee_types ft ON ft.fee_type_id = sf.fee_type_id
            WHERE ft.academic_year = %s
            """,
            (academic_year,),
            fetch=True
        ) or []
        row = rows[0] if rows else {}
        return {'total_amount': float(row.get('total_amount') or 0), 'payment_count': int(row.get('payment_count') or 0)}

    @classmethod
    def get_collected_by_fee_type_for_term(cls, academic_year: str = None, term: str = None) -> List[Dict[str, Any]]:
        start_date, end_date = config.Config.get_term_date_bounds(term or config.Config.CURRENT_TERM)
        return cls.get_collected_by_fee_type_for_view(academic_year, term, start_date, end_date)

    @classmethod
    def get_collected_by_fee_type_for_view(
        cls,
        academic_year: str = None,
        term: str = None,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        term = config.Config.normalize_term_name(term or config.Config.CURRENT_TERM)
        aliases = config.Config.get_term_aliases(term) or [term]
        alias_placeholders = ", ".join(["%s"] * len(aliases))

        if start_date and end_date:
            selected_payment_expr = "sf.payment_date BETWEEN %s AND %s"
            params = [start_date, end_date, start_date, end_date, academic_year]
        else:
            selected_payment_expr = f"ft.term IN ({alias_placeholders})"
            params = list(aliases) + list(aliases) + [academic_year]

        return db.execute_query(
            f"""
            SELECT MIN(ft.fee_type_id) AS fee_type_id,
                   ft.fee_name,
                   {db.group_concat_distinct("ft.term", "', '")} AS fee_terms,
                   COALESCE(SUM(CASE WHEN {selected_payment_expr} THEN sf.amount_paid ELSE 0 END), 0) AS term_collected,
                   COALESCE(SUM(sf.amount_paid), 0) AS academic_year_collected,
                   COUNT(CASE WHEN {selected_payment_expr} THEN sf.fee_id END) AS term_payment_count
            FROM fee_types ft
            LEFT JOIN student_fees sf ON sf.fee_type_id = ft.fee_type_id
            WHERE ft.academic_year = %s
            GROUP BY ft.fee_name
            ORDER BY term_collected DESC, ft.fee_name
            """,
            tuple(params),
            fetch=True
        ) or []


