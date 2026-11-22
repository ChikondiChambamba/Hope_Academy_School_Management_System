"""Expense model and term-scoped expense queries."""
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import config
from database.connection import db
from database.queries import Queries

@dataclass
class Expense:
    """Expense model"""
    
    expense_id: Optional[int] = None
    expense_date: Optional[date] = None
    item_id: Optional[int] = None
    description: str = ""
    amount: float = 0.0
    category: str = ""
    academic_year: str = ""
    term: str = ""
    payment_method: str = "Cash"
    receipt_number: str = ""
    notes: str = ""
    created_at: Optional[datetime] = None
    
    # Joined field
    item_name: str = ""

    @staticmethod
    def ensure_term_columns() -> None:
        """Ensure expenses can be scoped to academic year and term (older MySQL databases)."""
        if db.manages_schema or not db.once('schema.expense_terms'):
            return
        try:
            if not db.column_exists('expenses', 'academic_year'):
                db.execute_query("ALTER TABLE expenses ADD COLUMN academic_year VARCHAR(32) NULL AFTER category")
            if not db.column_exists('expenses', 'term'):
                db.execute_query("ALTER TABLE expenses ADD COLUMN term VARCHAR(32) NULL AFTER academic_year")
        except Exception:
            pass

    @staticmethod
    def _term_scope_filter(academic_year: str = None, term: str = None) -> tuple[str, tuple]:
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        term = config.Config.normalize_term_name(term or config.Config.CURRENT_TERM)
        aliases = config.Config.get_term_aliases(term) or [term]
        placeholders = ", ".join(["%s"] * len(aliases))
        start_raw, end_raw = config.Config.get_term_date_range(term)
        if start_raw and end_raw:
            return (
                f"""(
                    (
                        academic_year = %s
                        AND term IN ({placeholders})
                        AND expense_date BETWEEN %s AND %s
                    )
                    OR (
                        expense_date BETWEEN %s AND %s
                        AND (academic_year IS NULL OR academic_year = '')
                        AND (term IS NULL OR term = '')
                    )
                )""",
                tuple([academic_year, *aliases, start_raw, end_raw, start_raw, end_raw])
            )

        return (
            f"(academic_year = %s AND term IN ({placeholders}))",
            tuple([academic_year, *aliases])
        )

    @classmethod
    def get_term_expenses(cls, academic_year: str = None, term: str = None, limit: int = None) -> List['Expense']:
        cls.ensure_term_columns()
        where_clause, params = cls._term_scope_filter(academic_year, term)
        limit_clause = "LIMIT %s" if limit else ""
        query_params = tuple(list(params) + ([limit] if limit else []))
        rows = db.execute_query(
            f"SELECT * FROM expenses WHERE {where_clause} ORDER BY expense_date DESC, created_at DESC {limit_clause}",
            query_params,
            fetch=True
        ) or []
        return [cls.from_dict(row) for row in rows]

    @classmethod
    def get_term_expense_total(cls, academic_year: str = None, term: str = None) -> float:
        cls.ensure_term_columns()
        where_clause, params = cls._term_scope_filter(academic_year, term)
        rows = db.execute_query(
            f"SELECT COALESCE(SUM(amount), 0) AS total_amount FROM expenses WHERE {where_clause}",
            params,
            fetch=True
        ) or []
        return float(rows[0].get('total_amount') or 0) if rows else 0.0

    @classmethod
    def get_term_category_breakdown(cls, academic_year: str = None, term: str = None) -> List[Dict[str, Any]]:
        cls.ensure_term_columns()
        where_clause, params = cls._term_scope_filter(academic_year, term)
        return db.execute_query(
            f"""
            SELECT category, COUNT(*) AS expense_count, COALESCE(SUM(amount), 0) AS total_amount
            FROM expenses
            WHERE {where_clause}
            GROUP BY category
            ORDER BY total_amount DESC
            """,
            params,
            fetch=True
        ) or []

    @classmethod
    def get_academic_year_expense_total(cls, academic_year: str = None) -> float:
        cls.ensure_term_columns()
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        rows = db.execute_query(
            "SELECT COALESCE(SUM(amount), 0) AS total_amount FROM expenses WHERE academic_year = %s",
            (academic_year,),
            fetch=True
        ) or []
        return float(rows[0].get('total_amount') or 0) if rows else 0.0
    
    def __post_init__(self):
        """Initialize after dataclass creation"""
        if isinstance(self.expense_date, str):
            self.expense_date = datetime.strptime(self.expense_date, '%Y-%m-%d').date()
        if not self.expense_date:
            self.expense_date = date.today()
    
    def validate(self) -> tuple[bool, str]:
        """Validate expense data"""
        if not self.description.strip():
            return False, "Description is required"
        
        if self.amount <= 0:
            return False, "Amount must be greater than 0"
        
        if not self.expense_date:
            return False, "Expense date is required"
        
        if self.expense_date > date.today():
            return False, "Expense date cannot be in the future"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save expense to database"""
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
            self.ensure_term_columns()
            if not self.academic_year:
                self.academic_year = config.Config.CURRENT_ACADEMIC_YEAR
            if not self.term:
                self.term = config.Config.normalize_term_name(config.Config.CURRENT_TERM)
            # Generate receipt number if not provided
            if not self.receipt_number:
                self.receipt_number = self.generate_receipt_number()
            
            query = """
                INSERT INTO expenses 
                (expense_date, item_id, description, amount, 
                 category, academic_year, term, payment_method, receipt_number, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.expense_date,
                self.item_id,
                self.description,
                self.amount,
                self.category,
                self.academic_year,
                self.term,
                self.payment_method,
                self.receipt_number,
                self.notes
            )
            
            self.expense_id = db.execute_query(query, params)
            return True, f"Expense recorded successfully. Receipt: {self.receipt_number}"
            
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def generate_receipt_number(self) -> str:
        """Generate unique receipt number for expense"""
        try:
            # Format: EXP-YYYYMMDD-XXXX
            date_str = datetime.now().strftime('%Y%m%d')
            
            # Get next sequence number for today
            query = """
                SELECT COUNT(*) as count 
                FROM expenses 
                WHERE receipt_number LIKE %s
            """
            pattern = f"EXP-{date_str}-%"
            result = db.execute_query(query, (pattern,), fetch=True)
            
            if result:
                next_num = result[0]['count'] + 1
            else:
                next_num = 1
            
            return f"EXP-{date_str}-{next_num:04d}"
        except:
            # Fallback
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            return f"EXP-{timestamp}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert expense to dictionary"""
        data = asdict(self)
        
        # Convert dates to strings
        if data['expense_date'] and isinstance(data['expense_date'], date):
            data['expense_date'] = data['expense_date'].isoformat()
        
        # Convert datetime to string
        if data['created_at'] and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Expense':
        """Create Expense instance from dictionary"""
        allowed = set(cls.__dataclass_fields__.keys())
        return cls(**{key: value for key, value in (data or {}).items() if key in allowed})
    
    @classmethod
    def get_all(cls) -> List['Expense']:
        """Get all expenses"""
        try:
            query = Queries.GET_ALL_EXPENSES
            results = db.execute_query(query, fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_date_range(cls, start_date: date, end_date: date) -> List['Expense']:
        """Get expenses within date range"""
        try:
            query = """
                SELECT * FROM expenses 
                WHERE expense_date BETWEEN %s AND %s
                ORDER BY expense_date DESC
            """
            results = db.execute_query(query, (start_date, end_date), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_total_expenses(cls, start_date: date = None, end_date: date = None) -> Dict:
        """Get total expenses for period"""
        try:
            if not start_date:
                start_date = date(date.today().year, 1, 1)
            if not end_date:
                end_date = date.today()
            
            query = Queries.GET_EXPENSES_BY_CATEGORY
            results = db.execute_query(query, (start_date, end_date), fetch=True)
            
            total = sum(r['total_amount'] for r in results)
            
            return {
                'total_amount': total,
                'category_breakdown': results
            }
        except:
            return {'total_amount': 0, 'category_breakdown': []}

