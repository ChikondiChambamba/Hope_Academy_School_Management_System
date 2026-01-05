"""
Financial models for fee and expense management
"""
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
import config
from database.connection import db
from database.queries import Queries

@dataclass
class FeeType:
    """Fee type model"""
    
    fee_type_id: Optional[int] = None
    fee_name: str = ""
    description: str = ""
    amount: float = 0.0
    term: str = ""
    academic_year: str = ""
    is_required: bool = True
    created_at: Optional[datetime] = None
    
    def validate(self) -> tuple[bool, str]:
        """Validate fee type data"""
        if not self.fee_name.strip():
            return False, "Fee name is required"
        
        if self.amount <= 0:
            return False, "Amount must be greater than 0"
        
        if not self.academic_year:
            return False, "Academic year is required"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save fee type to database"""
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
            fee_data = self.to_dict()
            
            if self.fee_type_id:  # Update
                query = """
                    UPDATE fee_types SET 
                    fee_name = %s, description = %s, amount = %s,
                    term = %s, academic_year = %s, is_required = %s
                    WHERE fee_type_id = %s
                """
                params = (
                    fee_data['fee_name'],
                    fee_data['description'],
                    fee_data['amount'],
                    fee_data['term'],
                    fee_data['academic_year'],
                    fee_data['is_required'],
                    self.fee_type_id
                )
                
                db.execute_query(query, params)
                return True, "Fee type updated successfully"
                
            else:  # Insert
                query = """
                    INSERT INTO fee_types 
                    (fee_name, description, amount, term, academic_year, is_required)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = (
                    fee_data['fee_name'],
                    fee_data['description'],
                    fee_data['amount'],
                    fee_data['term'],
                    fee_data['academic_year'],
                    fee_data['is_required']
                )
                
                fee_type_id = db.execute_query(query, params)
                self.fee_type_id = fee_type_id
                return True, f"Fee type added successfully with ID: {fee_type_id}"
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert fee type to dictionary"""
        data = asdict(self)
        
        # Convert datetime to string
        if data['created_at'] and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FeeType':
        """Create FeeType instance from dictionary"""
        return cls(**data)
    
    @classmethod
    def get_all(cls, academic_year: str = None) -> List['FeeType']:
        """Get all fee types for academic year"""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        
        try:
            query = Queries.GET_FEE_TYPES
            results = db.execute_query(query, (academic_year,), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_id(cls, fee_type_id: int) -> Optional['FeeType']:
        """Get fee type by ID"""
        try:
            query = "SELECT * FROM fee_types WHERE fee_type_id = %s"
            result = db.execute_query(query, (fee_type_id,), fetch=True)
            if result:
                return cls.from_dict(result[0])
            return None
        except:
            return None


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
        
        try:
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
            return True, f"Payment recorded successfully. Receipt: {self.receipt_number}"
            
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def generate_receipt_number(self) -> str:
        """Generate unique receipt number"""
        try:
            # Format: REC-YYYYMMDD-XXXX
            date_str = datetime.now().strftime('%Y%m%d')
            
            # Get next sequence number for today
            query = """
                SELECT COUNT(*) as count 
                FROM student_fees 
                WHERE receipt_number LIKE %s
            """
            pattern = f"REC-{date_str}-%"
            result = db.execute_query(query, (pattern,), fetch=True)
            
            if result:
                next_num = result[0]['count'] + 1
            else:
                next_num = 1
            
            return f"REC-{date_str}-{next_num:04d}"
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
        """Create FeePayment instance from dictionary"""
        return cls(**data)
    
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


@dataclass
class Expense:
    """Expense model"""
    
    expense_id: Optional[int] = None
    expense_date: Optional[date] = None
    item_id: Optional[int] = None
    description: str = ""
    amount: float = 0.0
    category: str = ""
    payment_method: str = "Cash"
    receipt_number: str = ""
    notes: str = ""
    created_at: Optional[datetime] = None
    
    # Joined field
    item_name: str = ""
    
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
            # Generate receipt number if not provided
            if not self.receipt_number:
                self.receipt_number = self.generate_receipt_number()
            
            query = """
                INSERT INTO expenses 
                (expense_date, item_id, description, amount, 
                 category, payment_method, receipt_number, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.expense_date,
                self.item_id,
                self.description,
                self.amount,
                self.category,
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
        return cls(**data)
    
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


class FinancialManager:
    """Manager for financial operations"""
    
    @staticmethod
    def get_financial_summary(start_date: date = None, end_date: date = None) -> Dict:
        """Get complete financial summary for period"""
        if not start_date:
            start_date = date(date.today().year, 1, 1)
        if not end_date:
            end_date = date.today()
        
        # Get fees collected
        fees_summary = FeePayment.get_total_collected(start_date, end_date)
        
        # Get expenses
        expenses_summary = Expense.get_total_expenses(start_date, end_date)
        
        # Calculate net balance
        total_fees = fees_summary['total_amount']
        total_expenses = expenses_summary['total_amount']
        net_balance = total_fees - total_expenses
        
        # Get student balances
        try:
            query = """
                SELECT 
                    SUM(balance) as total_outstanding
                FROM student_fee_summary
                WHERE academic_year = %s
            """
            result = db.execute_query(query, (config.Config.CURRENT_ACADEMIC_YEAR,), fetch=True)
            total_outstanding = result[0]['total_outstanding'] if result else 0
        except:
            total_outstanding = 0
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'revenue': {
                'total_fees': total_fees,
                'payment_count': fees_summary['payment_count'],
                'monthly_breakdown': fees_summary['monthly_breakdown']
            },
            'expenses': {
                'total_expenses': total_expenses,
                'category_breakdown': expenses_summary['category_breakdown']
            },
            'net_balance': net_balance,
            'outstanding_fees': total_outstanding,
            'cash_position': net_balance  # Simplified cash position
        }
    
    @staticmethod
    def get_student_balances(academic_year: str = None) -> List[Dict]:
        """Get all student balances"""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        
        try:
            query = """
                SELECT 
                    s.student_id,
                    s.student_code,
                    CONCAT(s.first_name, ' ', s.last_name) as student_name,
                    s.class,
                    COALESCE(SUM(ft.amount), 0) as total_due,
                    COALESCE(SUM(sf.amount_paid), 0) as total_paid,
                    COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) as balance
                FROM students s
                CROSS JOIN fee_types ft
                LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                WHERE s.is_active = 1 AND ft.academic_year = %s
                GROUP BY s.student_id, s.student_code, s.first_name, s.last_name, s.class
                ORDER BY balance DESC, s.class, s.last_name
            """
            return db.execute_query(query, (academic_year,), fetch=True)
        except:
            return []
    
    @staticmethod
    def get_top_payers(limit: int = 10) -> List[Dict]:
        """Get top fee payers"""
        try:
            query = """
                SELECT 
                    s.student_id,
                    s.student_code,
                    CONCAT(s.first_name, ' ', s.last_name) as student_name,
                    s.class,
                    COALESCE(SUM(sf.amount_paid), 0) as total_paid,
                    COUNT(sf.fee_id) as payment_count
                FROM students s
                LEFT JOIN student_fees sf ON s.student_id = sf.student_id
                WHERE s.is_active = 1
                GROUP BY s.student_id, s.student_code, s.first_name, s.last_name, s.class
                ORDER BY total_paid DESC
                LIMIT %s
            """
            return db.execute_query(query, (limit,), fetch=True)
        except:
            return []
    
    @staticmethod
    def get_revenue_trend(days: int = 30) -> List[Dict]:
        """Get daily revenue trend for specified days"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            query = """
                SELECT 
                    payment_date as date,
                    SUM(amount_paid) as daily_revenue,
                    COUNT(*) as payment_count
                FROM student_fees
                WHERE payment_date BETWEEN %s AND %s
                GROUP BY payment_date
                ORDER BY payment_date
            """
            return db.execute_query(query, (start_date, end_date), fetch=True)
        except:
            return []