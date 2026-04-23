
"""
Financial models for fee and expense management
"""
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
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

    @classmethod
    def get_applicable_for_class(cls, class_name: str, academic_year: str = None, term: str = None) -> List['FeeType']:
        """Get fee types applicable to a class (or globally applicable when no class mapping exists)."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        if not term:
            term = config.Config.CURRENT_TERM
        class_name = (class_name or "").strip()
        if not class_name:
            return cls.get_all(academic_year)
        try:
            query = """
                SELECT ft.*
                FROM fee_types ft
                WHERE ft.academic_year = %s
                  AND (
                        ft.term = %s
                        OR ft.term IS NULL
                        OR ft.term = ''
                        OR NOT EXISTS (
                            SELECT 1
                            FROM fee_types ftx
                            WHERE ftx.academic_year = %s
                              AND ftx.term = %s
                        )
                  )
                  AND (
                        NOT EXISTS (
                            SELECT 1 FROM fee_type_classes ftc0
                            WHERE ftc0.fee_type_id = ft.fee_type_id
                        )
                        OR EXISTS (
                            SELECT 1
                            FROM fee_type_classes ftc
                            JOIN classes c ON c.class_id = ftc.class_id
                            WHERE ftc.fee_type_id = ft.fee_type_id
                              AND LOWER(c.class_name) = LOWER(%s)
                              AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                        )
                  )
                ORDER BY ft.fee_name
            """
            results = db.execute_query(query, (academic_year, term, academic_year, term, class_name, academic_year), fetch=True)
            return [cls.from_dict(row) for row in (results or [])]
        except Exception:
            # Fallback to previous behavior if mapping table is unavailable
            return cls.get_all(academic_year)

    @classmethod
    def is_applicable_to_class(cls, fee_type_id: int, class_name: str, academic_year: str = None) -> bool:
        """Return True if fee type is applicable to the given class."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        class_name = (class_name or "").strip()
        if not fee_type_id:
            return False
        if not class_name:
            return True
        try:
            query = """
                SELECT
                    CASE
                        WHEN NOT EXISTS (
                            SELECT 1 FROM fee_type_classes ftc0
                            WHERE ftc0.fee_type_id = %s
                        ) THEN 1
                        WHEN EXISTS (
                            SELECT 1
                            FROM fee_type_classes ftc
                            JOIN classes c ON c.class_id = ftc.class_id
                            WHERE ftc.fee_type_id = %s
                              AND LOWER(c.class_name) = LOWER(%s)
                              AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                        ) THEN 1
                        ELSE 0
                    END AS allowed
            """
            res = db.execute_query(query, (fee_type_id, fee_type_id, class_name, academic_year), fetch=True)
            return bool(res and int(res[0].get('allowed') or 0) == 1)
        except Exception:
            # Fallback to permissive behavior to avoid hard failures on old DBs
            return True


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

                # After successful payment, apply business rules:
                # - If this payment is for a tuition fee, exempt other tuition fee types for this student.
                try:
                    ft = FeeType.get_by_id(self.fee_type_id)
                    if ft and 'tuition' in ft.fee_name.lower():
                        # find other tuition fee types for this academic year
                        other_tuitions = db.execute_query(
                            "SELECT fee_type_id FROM fee_types WHERE academic_year = %s AND LOWER(fee_name) LIKE %s AND fee_type_id != %s",
                            (ft.academic_year, '%tuition%', ft.fee_type_id),
                            fetch=True
                        )
                        if other_tuitions:
                            for row in other_tuitions:
                                try:
                                    db.execute_query(
                                        "INSERT IGNORE INTO student_fee_exemptions (student_id, fee_type_id, reason) VALUES (%s, %s, %s)",
                                        (self.student_id, row['fee_type_id'], f"Exempted because tuition {ft.fee_type_id} paid")
                                    )
                                except Exception:
                                    pass

                except Exception:
                    pass

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

            # Use a DB-backed daily sequence to avoid race conditions.
            # Insert a new row for today or increment existing row atomically using
            # MySQL's ON DUPLICATE KEY UPDATE behavior.
            try:
                upsert = """
                    INSERT INTO receipt_sequence (seq_date, seq) VALUES (%s, 1)
                    ON DUPLICATE KEY UPDATE seq = seq + 1
                """
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
    def _ensure_term_rollover_tables() -> None:
        """Ensure tables used by term rollover logic exist."""
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS term_changes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                academic_year VARCHAR(32) NOT NULL,
                previous_term VARCHAR(32),
                term_name VARCHAR(32) NOT NULL,
                start_date DATE,
                rollover_processed TINYINT(1) DEFAULT 0,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_term_change_year_term (academic_year, term_name)
            ) ENGINE=InnoDB
            """
        )
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS student_term_fee_rollovers (
                rollover_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                from_academic_year VARCHAR(32) NOT NULL,
                from_term VARCHAR(32) NOT NULL,
                to_academic_year VARCHAR(32) NOT NULL,
                to_term VARCHAR(32) NOT NULL,
                carried_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
                source_total_due DECIMAL(12,2) NOT NULL DEFAULT 0,
                source_total_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_student_to_term (student_id, to_academic_year, to_term),
                INDEX idx_rollover_target (to_academic_year, to_term),
                INDEX idx_rollover_source (from_academic_year, from_term),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        # Backward-compatible migration for older term_changes tables.
        try:
            cols = db.execute_query(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'term_changes'
                """,
                fetch=True
            ) or []
            col_names = {row.get('COLUMN_NAME') for row in cols}

            if 'previous_term' not in col_names:
                db.execute_query("ALTER TABLE term_changes ADD COLUMN previous_term VARCHAR(32) NULL AFTER academic_year")
            if 'rollover_processed' not in col_names:
                db.execute_query("ALTER TABLE term_changes ADD COLUMN rollover_processed TINYINT(1) DEFAULT 0 AFTER start_date")
        except Exception:
            pass

    @staticmethod
    def _ensure_salary_monthly_table() -> None:
        """Ensure monthly salary snapshot table exists."""
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS teacher_salary_monthly (
                payroll_id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_id INT NOT NULL,
                payroll_month VARCHAR(7) NOT NULL,
                base_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
                allowance_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                advances_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                gross_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
                net_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
                is_paid TINYINT(1) NOT NULL DEFAULT 0,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_teacher_month (teacher_id, payroll_month),
                INDEX idx_salary_month (payroll_month),
                FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS term_rollover_runs (
                run_id INT AUTO_INCREMENT PRIMARY KEY,
                academic_year VARCHAR(32) NOT NULL,
                from_term VARCHAR(32) NOT NULL,
                to_term VARCHAR(32) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'PREVIEW',
                total_students INT NOT NULL DEFAULT 0,
                reset_students INT NOT NULL DEFAULT 0,
                carry_students INT NOT NULL DEFAULT 0,
                previous_outstanding_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                new_term_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                carry_forward_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                opening_balance_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                executed_by VARCHAR(100),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                INDEX idx_rollover_run_lookup (academic_year, from_term, to_term, status)
            ) ENGINE=InnoDB
            """
        )
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS term_rollover_run_items (
                item_id INT AUTO_INCREMENT PRIMARY KEY,
                run_id INT NOT NULL,
                student_id INT NOT NULL,
                student_code VARCHAR(20),
                student_name VARCHAR(150),
                class_name VARCHAR(50),
                previous_outstanding DECIMAL(12,2) NOT NULL DEFAULT 0,
                new_term_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                carry_forward_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                reset_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                opening_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
                payment_status VARCHAR(20) NOT NULL DEFAULT 'Paid',
                carry_status VARCHAR(20) NOT NULL DEFAULT 'Reset',
                details_json LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_rollover_run_student (run_id, student_id),
                INDEX idx_rollover_item_student (student_id),
                FOREIGN KEY (run_id) REFERENCES term_rollover_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS student_term_fee_rollover_items (
                rollover_item_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                from_academic_year VARCHAR(32) NOT NULL,
                from_term VARCHAR(32) NOT NULL,
                to_academic_year VARCHAR(32) NOT NULL,
                to_term VARCHAR(32) NOT NULL,
                source_fee_type_id INT NULL,
                source_fee_name VARCHAR(100) NOT NULL,
                source_is_required TINYINT(1) NOT NULL DEFAULT 1,
                source_is_class_specific TINYINT(1) NOT NULL DEFAULT 0,
                source_expected_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                source_paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                carried_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                source_status VARCHAR(20) NOT NULL DEFAULT 'Paid',
                target_fee_type_id INT NULL,
                target_fee_name VARCHAR(100),
                target_applicable TINYINT(1) NOT NULL DEFAULT 0,
                run_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_rollover_student_source_target (
                    student_id, from_academic_year, from_term, to_academic_year, to_term, source_fee_name
                ),
                INDEX idx_rollover_items_target (to_academic_year, to_term),
                INDEX idx_rollover_items_student (student_id),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        # Backward-compatible migration for older monthly salary tables.
        try:
            cols = db.execute_query(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'teacher_salary_monthly'
                """,
                fetch=True
            ) or []
            col_names = {row.get('COLUMN_NAME') for row in cols}
            if 'is_paid' not in col_names:
                db.execute_query("ALTER TABLE teacher_salary_monthly ADD COLUMN is_paid TINYINT(1) NOT NULL DEFAULT 0 AFTER net_salary")
        except Exception:
            pass

    @staticmethod
    def _get_next_term_name(current_term: str) -> str:
        """Return the next configured term name."""
        terms = list(getattr(config.Config, 'TERMS', ['Term 1', 'Term 2', 'Term 3'])) or ['Term 1', 'Term 2', 'Term 3']
        if current_term in terms:
            idx = terms.index(current_term)
            return terms[(idx + 1) % len(terms)]
        return terms[0]

    @staticmethod
    def _student_fee_rows_for_term(academic_year: str, term: str) -> List[Dict[str, Any]]:
        """Return one row per student/fee type for a specific term."""
        FinancialManager._ensure_term_rollover_tables()
        from database.queries import student_is_new_available

        is_new_guard = "AND s.is_new = 0" if student_is_new_available() else "AND 1=0"
        query = f"""
            SELECT
                s.student_id,
                s.student_code,
                CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                s.class AS class_name,
                ft.fee_type_id,
                ft.fee_name,
                ft.is_required,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM fee_type_classes ftc0
                        WHERE ftc0.fee_type_id = ft.fee_type_id
                    ) THEN 1 ELSE 0
                END AS is_class_specific,
                CASE
                    WHEN sfe.exemption_id IS NOT NULL THEN 0
                    WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') {is_new_guard} THEN 0
                    WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                    WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                    ELSE ft.amount
                END AS expected_amount,
                COALESCE(sf.amount_paid, 0) AS paid_amount
            FROM students s
            JOIN fee_types ft
              ON ft.academic_year = %s
             AND ft.term = %s
            LEFT JOIN student_fee_exemptions sfe
              ON sfe.student_id = s.student_id
             AND sfe.fee_type_id = ft.fee_type_id
            LEFT JOIN (
                SELECT student_id, fee_type_id, COALESCE(SUM(amount_paid), 0) AS amount_paid
                FROM student_fees
                GROUP BY student_id, fee_type_id
            ) sf ON sf.student_id = s.student_id AND sf.fee_type_id = ft.fee_type_id
            WHERE s.is_active = 1
              AND (
                    NOT EXISTS (
                        SELECT 1 FROM fee_type_classes ftc0
                        WHERE ftc0.fee_type_id = ft.fee_type_id
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM fee_type_classes ftc
                        JOIN classes c ON c.class_id = ftc.class_id
                        WHERE ftc.fee_type_id = ft.fee_type_id
                          AND LOWER(c.class_name) = LOWER(s.class)
                          AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                    )
              )
            ORDER BY s.class, s.last_name, s.first_name, ft.fee_name
        """
        return db.execute_query(query, (academic_year, term, academic_year), fetch=True) or []

    @staticmethod
    def _get_term_fee_templates(academic_year: str, term: str) -> List[Dict[str, Any]]:
        """Return fee type definitions and class scopes for a term."""
        rows = db.execute_query(
            """
            SELECT
                ft.fee_type_id,
                ft.fee_name,
                ft.description,
                ft.amount,
                ft.term,
                ft.academic_year,
                ft.is_required,
                GROUP_CONCAT(DISTINCT CAST(ftc.class_id AS CHAR) ORDER BY ftc.class_id SEPARATOR ',') AS class_ids,
                GROUP_CONCAT(DISTINCT LOWER(c.class_name) ORDER BY LOWER(c.class_name) SEPARATOR '||') AS class_names
            FROM fee_types ft
            LEFT JOIN fee_type_classes ftc
              ON ftc.fee_type_id = ft.fee_type_id
             AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
            LEFT JOIN classes c ON c.class_id = ftc.class_id
            WHERE ft.academic_year = %s
              AND ft.term = %s
            GROUP BY
                ft.fee_type_id, ft.fee_name, ft.description, ft.amount, ft.term, ft.academic_year, ft.is_required
            ORDER BY ft.fee_name, ft.fee_type_id
            """,
            (academic_year, academic_year, term),
            fetch=True
        ) or []

        templates: List[Dict[str, Any]] = []
        for row in rows:
            class_ids = []
            for raw_id in (row.get('class_ids') or '').split(','):
                raw_id = raw_id.strip()
                if raw_id:
                    try:
                        class_ids.append(int(raw_id))
                    except ValueError:
                        pass
            class_names = [name.strip().lower() for name in (row.get('class_names') or '').split('||') if name.strip()]
            templates.append({
                'fee_type_id': row.get('fee_type_id'),
                'fee_name': row.get('fee_name') or '',
                'description': row.get('description') or '',
                'amount': float(row.get('amount') or 0),
                'term': row.get('term') or '',
                'academic_year': row.get('academic_year') or academic_year,
                'is_required': bool(row.get('is_required')),
                'class_ids': class_ids,
                'class_names': class_names
            })
        return templates

    @staticmethod
    def _fee_template_signature(template: Dict[str, Any]) -> tuple:
        """Build a signature that prevents duplicate fee cloning."""
        scope = tuple(sorted((template.get('class_names') or [])))
        return (
            (template.get('fee_name') or '').strip().lower(),
            bool(template.get('is_required')),
            scope
        )

    @staticmethod
    def _build_projected_term_fee_rows(
        academic_year: str,
        from_term: str,
        to_term: str
    ) -> tuple[List[Dict[str, Any]], int]:
        """Project next-term student fee rows, inheriting missing fee types from the previous term."""
        from database.queries import student_is_new_available

        target_templates = FinancialManager._get_term_fee_templates(academic_year, to_term)
        source_templates = FinancialManager._get_term_fee_templates(academic_year, from_term)
        existing_signatures = {FinancialManager._fee_template_signature(t) for t in target_templates}

        effective_templates = list(target_templates)
        inherited_templates = 0
        for template in source_templates:
            signature = FinancialManager._fee_template_signature(template)
            if signature in existing_signatures:
                continue
            inherited_templates += 1
            effective_templates.append({
                **template,
                'fee_type_id': None,
                'term': to_term,
                'academic_year': academic_year
            })
            existing_signatures.add(signature)

        if not effective_templates:
            return [], 0

        student_rows = db.execute_query(
            """
            SELECT
                student_id,
                student_code,
                CONCAT(first_name, ' ', last_name) AS student_name,
                class
                {is_new_column}
            FROM students
            WHERE is_active = 1
            ORDER BY class, last_name, first_name
            """.format(is_new_column=", is_new" if student_is_new_available() else ""),
            fetch=True
        ) or []

        projected_rows: List[Dict[str, Any]] = []
        for student in student_rows:
            student_class = (student.get('class') or '').strip().lower()
            is_new_student = bool(student.get('is_new')) if student_is_new_available() else False
            for template in effective_templates:
                class_scope = template.get('class_names') or []
                if class_scope and student_class not in class_scope:
                    continue

                fee_name = template.get('fee_name') or ''
                expected_amount = float(template.get('amount') or 0)
                lower_fee_name = fee_name.lower()
                if ('registration' in lower_fee_name or 'uniform' in lower_fee_name) and not is_new_student:
                    expected_amount = 0.0
                elif 'tuition' in lower_fee_name and ('nursery' in student_class or 'reception' in student_class):
                    expected_amount = 45000.0
                elif 'tuition' in lower_fee_name:
                    expected_amount = 85000.0

                projected_rows.append({
                    'student_id': student.get('student_id'),
                    'student_code': student.get('student_code') or '',
                    'student_name': student.get('student_name') or '',
                    'class_name': student.get('class') or '',
                    'fee_type_id': template.get('fee_type_id'),
                    'fee_name': fee_name,
                    'is_required': 1 if template.get('is_required') else 0,
                    'is_class_specific': 1 if class_scope else 0,
                    'expected_amount': expected_amount,
                    'paid_amount': 0.0
                })
        return projected_rows, inherited_templates

    @staticmethod
    def _clone_missing_fee_types_to_term(connection, academic_year: str, from_term: str, to_term: str) -> int:
        """Copy missing fee types and class mappings from one term to another inside a transaction."""
        source_templates = FinancialManager._get_term_fee_templates(academic_year, from_term)
        target_templates = FinancialManager._get_term_fee_templates(academic_year, to_term)
        existing_signatures = {FinancialManager._fee_template_signature(t) for t in target_templates}
        cloned = 0

        for template in source_templates:
            signature = FinancialManager._fee_template_signature(template)
            if signature in existing_signatures:
                continue

            new_fee_type_id = db.execute_query_in_transaction(
                connection,
                """
                INSERT INTO fee_types (fee_name, description, amount, term, academic_year, is_required)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    template.get('fee_name') or '',
                    template.get('description') or '',
                    float(template.get('amount') or 0),
                    to_term,
                    academic_year,
                    1 if template.get('is_required') else 0
                )
            )

            for class_id in template.get('class_ids') or []:
                db.execute_query_in_transaction(
                    connection,
                    """
                    INSERT IGNORE INTO fee_type_classes (fee_type_id, class_id, academic_year)
                    VALUES (%s, %s, %s)
                    """,
                    (new_fee_type_id, class_id, academic_year)
                )

            existing_signatures.add(signature)
            cloned += 1

        return cloned

    @staticmethod
    def _existing_carried_rows_for_term(academic_year: str, term: str) -> List[Dict[str, Any]]:
        """Return previously carried-forward fee items that still affect the given term."""
        FinancialManager._ensure_term_rollover_tables()
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
              AND COALESCE(ri.carried_amount, 0) > 0
              AND s.is_active = 1
            ORDER BY s.class, s.last_name, s.first_name, ri.source_fee_name
        """
        return db.execute_query(query, (academic_year, term), fetch=True) or []

    @staticmethod
    def _next_term_fee_lookup(academic_year: str, term: str) -> Dict[tuple, Dict[str, Any]]:
        """Build next-term fee lookup by normalized fee name and class."""
        rows = FinancialManager._student_fee_rows_for_term(academic_year, term)
        lookup: Dict[tuple, Dict[str, Any]] = {}
        for row in rows:
            key = (int(row.get('student_id') or 0), (row.get('fee_name') or '').strip().lower())
            lookup[key] = row
        return lookup

    @staticmethod
    def _build_term_rollover_preview(academic_year: str, from_term: str, to_term: str) -> Dict[str, Any]:
        """Build deterministic preview data for a term rollover."""
        source_fee_rows = FinancialManager._student_fee_rows_for_term(academic_year, from_term)
        next_term_rows = FinancialManager._student_fee_rows_for_term(academic_year, to_term)
        existing_carry_rows = FinancialManager._existing_carried_rows_for_term(academic_year, from_term)
        warnings: List[str] = []
        projected_next_term_rows, inherited_templates = FinancialManager._build_projected_term_fee_rows(
            academic_year,
            from_term,
            to_term
        )
        if inherited_templates > 0:
            next_term_rows = projected_next_term_rows
            warnings.append(
                f"{inherited_templates} fee types from {from_term} will be copied into {to_term} during rollover."
            )
        elif not next_term_rows:
            warnings.append(f"No fee types are configured for {to_term} in {academic_year}. New term fees will remain 0 until fee types are added.")

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
                    'reset_amount': 0.0,
                    'opening_balance': 0.0,
                    'payment_status': 'Paid',
                    'carry_status': 'Reset',
                    'details': []
                }
            return student_map[sid]

        next_lookup: Dict[tuple, Dict[str, Any]] = {}
        for row in next_term_rows:
            key = (int(row.get('student_id') or 0), (row.get('fee_name') or '').strip().lower())
            next_lookup[key] = row

        for row in source_fee_rows:
            student = ensure_student(row)
            expected = float(row.get('expected_amount') or 0)
            paid = float(row.get('paid_amount') or 0)
            outstanding = max(expected - paid, 0.0)
            if outstanding <= 0:
                continue

            fee_name = row.get('fee_name') or ''
            is_required = bool(row.get('is_required'))
            is_class_specific = bool(row.get('is_class_specific'))
            target = next_lookup.get((student['student_id'], fee_name.strip().lower()))
            target_applicable = target is not None

            should_carry = is_required or ((not is_required or is_class_specific) and target_applicable)
            carried_amount = outstanding if should_carry else 0.0
            reset_amount = 0.0 if should_carry else outstanding

            student['previous_fee_outstanding'] += outstanding
            student['carry_forward_total'] += carried_amount
            student['reset_amount'] += reset_amount
            student['details'].append({
                'source': 'previous_term_fee',
                'fee_type_id': row.get('fee_type_id'),
                'fee_name': fee_name,
                'expected_amount': expected,
                'paid_amount': paid,
                'outstanding': outstanding,
                'is_required': is_required,
                'is_class_specific': is_class_specific,
                'target_fee_type_id': target.get('fee_type_id') if target else None,
                'target_applicable': target_applicable,
                'carried_amount': carried_amount,
                'reset_amount': reset_amount,
                'status': 'Carried Forward' if carried_amount > 0 else 'Reset'
            })

        for row in existing_carry_rows:
            student = ensure_student(row)
            carry_amount = float(row.get('carried_amount') or 0)
            if carry_amount <= 0:
                continue

            fee_name = row.get('source_fee_name') or 'Carried Balance'
            is_required = bool(row.get('source_is_required'))
            is_class_specific = bool(row.get('source_is_class_specific'))
            target = next_lookup.get((student['student_id'], fee_name.strip().lower()))
            target_applicable = target is not None
            should_carry = is_required or ((not is_required or is_class_specific) and target_applicable)
            carried_amount = carry_amount if should_carry else 0.0
            reset_amount = 0.0 if should_carry else carry_amount

            student['existing_carried_in'] += carry_amount
            student['carry_forward_total'] += carried_amount
            student['reset_amount'] += reset_amount
            student['details'].append({
                'source': 'prior_carry',
                'fee_type_id': None,
                'fee_name': fee_name,
                'expected_amount': carry_amount,
                'paid_amount': 0.0,
                'outstanding': carry_amount,
                'is_required': is_required,
                'is_class_specific': is_class_specific,
                'target_fee_type_id': target.get('fee_type_id') if target else None,
                'target_applicable': target_applicable,
                'carried_amount': carried_amount,
                'reset_amount': reset_amount,
                'status': 'Carried Forward' if carried_amount > 0 else 'Reset'
            })

        for row in next_term_rows:
            student = ensure_student(row)
            student['new_term_total'] += float(row.get('expected_amount') or 0)

        preview_rows = []
        for student in student_map.values():
            student['previous_outstanding'] = student['previous_fee_outstanding'] + student['existing_carried_in']
            student['opening_balance'] = student['new_term_total'] + student['carry_forward_total']
            if student['previous_outstanding'] <= 0:
                student['payment_status'] = 'Paid'
            elif student['previous_outstanding'] < student['new_term_total'] + student['carry_forward_total']:
                student['payment_status'] = 'Partial'
            else:
                student['payment_status'] = 'Unpaid'
            student['carry_status'] = 'Carried Forward' if student['carry_forward_total'] > 0 else 'Reset'
            preview_rows.append(student)

        preview_rows.sort(key=lambda r: (r.get('class') or '', r.get('student_name') or ''))
        summary = {
            'total_students': len(preview_rows),
            'reset_students': sum(1 for r in preview_rows if float(r.get('carry_forward_total') or 0) <= 0),
            'carry_students': sum(1 for r in preview_rows if float(r.get('carry_forward_total') or 0) > 0),
            'previous_outstanding_total': round(sum(float(r.get('previous_outstanding') or 0) for r in preview_rows), 2),
            'new_term_total': round(sum(float(r.get('new_term_total') or 0) for r in preview_rows), 2),
            'carry_forward_total': round(sum(float(r.get('carry_forward_total') or 0) for r in preview_rows), 2),
            'opening_balance_total': round(sum(float(r.get('opening_balance') or 0) for r in preview_rows), 2)
        }
        return {
            'academic_year': academic_year,
            'from_term': from_term,
            'to_term': to_term,
            'rows': preview_rows,
            'summary': summary,
            'warnings': warnings,
            'projected_fee_type_copies': inherited_templates
        }

    @staticmethod
    def get_term_rollover_preview(
        academic_year: str = None,
        from_term: str = None,
        to_term: str = None
    ) -> Dict[str, Any]:
        """Return rollover preview and persist a preview snapshot record."""
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        from_term = from_term or config.Config.CURRENT_TERM
        to_term = to_term or FinancialManager._get_next_term_name(from_term)

        preview = FinancialManager._build_term_rollover_preview(academic_year, from_term, to_term)
        summary = preview['summary']
        executed_by = getattr(config.Config, 'CURRENT_USER', None) or 'System'
        run_id = db.execute_query(
            """
            INSERT INTO term_rollover_runs (
                academic_year, from_term, to_term, status, total_students, reset_students, carry_students,
                previous_outstanding_total, new_term_total, carry_forward_total, opening_balance_total, executed_by
            )
            VALUES (%s, %s, %s, 'PREVIEW', %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                academic_year,
                from_term,
                to_term,
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

        item_params = []
        for row in preview['rows']:
            import json
            item_params.append((
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
            ))
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

    @staticmethod
    def _month_bounds(year_month: str) -> tuple[date, date]:
        """Return [start, next_month_start) bounds for YYYY-MM."""
        start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        if start.month == 12:
            end_exclusive = date(start.year + 1, 1, 1)
        else:
            end_exclusive = date(start.year, start.month + 1, 1)
        return start, end_exclusive

    @staticmethod
    def generate_monthly_salary_snapshot(year_month: str = None) -> None:
        """Compute and persist salary snapshot for a given month (YYYY-MM)."""
        if not year_month:
            year_month = date.today().strftime("%Y-%m")
        FinancialManager._ensure_salary_monthly_table()
        start_date, end_exclusive = FinancialManager._month_bounds(year_month)

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
            ON DUPLICATE KEY UPDATE
                base_salary = VALUES(base_salary),
                allowance_amount = VALUES(allowance_amount),
                advances_amount = VALUES(advances_amount),
                gross_salary = VALUES(gross_salary),
                net_salary = VALUES(net_salary),
                generated_at = CURRENT_TIMESTAMP
            """,
            (year_month, start_date, end_exclusive)
        )

    @staticmethod
    def get_latest_rollover_run() -> Dict[str, Any]:
        """Return the most recent completed rollover run."""
        FinancialManager._ensure_term_rollover_tables()
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
    def execute_term_rollover(
        academic_year: str = None,
        from_term: str = None,
        to_term: str = None,
        term_start_date: str = None
    ) -> Dict[str, Any]:
        """Execute term rollover transactionally and persist detail rows."""
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        from_term = from_term or config.Config.CURRENT_TERM
        to_term = to_term or FinancialManager._get_next_term_name(from_term)
        preview = FinancialManager._build_term_rollover_preview(academic_year, from_term, to_term)
        summary = preview['summary']
        executed_by = getattr(config.Config, 'CURRENT_USER', None) or 'System'

        with db.transaction() as connection:
            cloned_fee_types = FinancialManager._clone_missing_fee_types_to_term(connection, academic_year, from_term, to_term)
            run_id = db.execute_query_in_transaction(
                connection,
                """
                INSERT INTO term_rollover_runs (
                    academic_year, from_term, to_term, status, total_students, reset_students, carry_students,
                    previous_outstanding_total, new_term_total, carry_forward_total, opening_balance_total, executed_by
                )
                VALUES (%s, %s, %s, 'RUNNING', %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    academic_year,
                    from_term,
                    to_term,
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

            for row in preview['rows']:
                import json
                db.execute_query_in_transaction(
                    connection,
                    """
                    INSERT INTO term_rollover_run_items (
                        run_id, student_id, student_code, student_name, class_name, previous_outstanding,
                        new_term_total, carry_forward_total, reset_amount, opening_balance,
                        payment_status, carry_status, details_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
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
                )

            # Replace any previously stored carry-forward detail rows for the new target term.
            db.execute_query_in_transaction(
                connection,
                """
                DELETE FROM student_term_fee_rollover_items
                WHERE to_academic_year = %s AND to_term = %s
                """,
                (academic_year, to_term)
            )
            db.execute_query_in_transaction(
                connection,
                """
                DELETE FROM student_term_fee_rollovers
                WHERE to_academic_year = %s AND to_term = %s
                """,
                (academic_year, to_term)
            )

            for row in preview['rows']:
                total_carried_for_student = 0.0
                for detail in row.get('details') or []:
                    carried_amount = float(detail.get('carried_amount') or 0)
                    if carried_amount <= 0:
                        continue
                    total_carried_for_student += carried_amount
                    db.execute_query_in_transaction(
                        connection,
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
                            row['student_id'],
                            academic_year,
                            from_term,
                            academic_year,
                            to_term,
                            detail.get('fee_type_id'),
                            detail.get('fee_name') or 'Carried Balance',
                            1 if detail.get('is_required') else 0,
                            1 if detail.get('is_class_specific') else 0,
                            float(detail.get('expected_amount') or 0),
                            float(detail.get('paid_amount') or 0),
                            carried_amount,
                            detail.get('status') or 'Carried Forward',
                            detail.get('target_fee_type_id'),
                            detail.get('fee_name') or 'Carried Balance',
                            1 if detail.get('target_applicable') else 0,
                            run_id
                        )
                    )

                db.execute_query_in_transaction(
                    connection,
                    """
                    INSERT INTO student_term_fee_rollovers (
                        student_id, from_academic_year, from_term, to_academic_year, to_term,
                        carried_balance, source_total_due, source_total_paid
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row['student_id'],
                        academic_year,
                        from_term,
                        academic_year,
                        to_term,
                        total_carried_for_student,
                        row['previous_outstanding'],
                        row['previous_outstanding'] - total_carried_for_student
                    )
                )

            db.execute_query_in_transaction(
                connection,
                """
                INSERT INTO term_changes (academic_year, previous_term, term_name, start_date, rollover_processed)
                VALUES (%s, %s, %s, %s, 1)
                """,
                (academic_year, from_term, to_term, term_start_date)
            )
            db.execute_query_in_transaction(
                connection,
                """
                UPDATE term_rollover_runs
                SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                (run_id,)
            )

        config.Config.PREVIOUS_ACADEMIC_YEAR = academic_year
        config.Config.PREVIOUS_TERM = from_term
        config.Config.CURRENT_TERM = to_term
        if term_start_date:
            config.Config.TERM_START_DATE = term_start_date
        config.Config.save_user_settings()

        preview['run_id'] = run_id
        preview['executed'] = True
        preview['cloned_fee_types'] = cloned_fee_types
        return preview
    
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
            balances = FinancialManager.get_student_balances(
                config.Config.CURRENT_ACADEMIC_YEAR,
                term=config.Config.CURRENT_TERM
            )
            total_outstanding = sum(float(r.get('balance') or 0) for r in balances if float(r.get('balance') or 0) > 0)
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
    def get_student_balances(academic_year: str = None, fee_type_id: int = None, term: str = None) -> List[Dict]:
        """Get student balances for a term, including carried balances from previous term."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        if not term:
            term = config.Config.CURRENT_TERM
        try:
            FinancialManager._ensure_term_rollover_tables()
            from database.queries import student_is_new_available
            is_new_guard = "AND s.is_new = 0" if student_is_new_available() else "AND 1=0"
            fee_filter = ""
            term_filter = """
                  AND (
                        ft.term = %s
                        OR ft.term IS NULL
                        OR ft.term = ''
                        OR NOT EXISTS (
                            SELECT 1
                            FROM fee_types ftx
                            WHERE ftx.academic_year = %s
                              AND ftx.term = %s
                        )
                  )
            """
            if fee_type_id:
                fee_filter = "AND ft.fee_type_id = %s"
                # When user filters by a specific fee type, respect that fee type regardless of term.
                term_filter = ""

            query = f"""
                SELECT
                    s.student_id,
                    s.student_code,
                    CONCAT(s.first_name, ' ', s.last_name) as student_name,
                    s.class,
                    COALESCE(SUM(
                        CASE
                            WHEN sfe.exemption_id IS NOT NULL THEN 0
                            WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') {is_new_guard} THEN 0
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                            ELSE ft.amount
                        END
                    ), 0) as total_fees,
                    COALESCE(SUM(sf.amount_paid), 0) as amount_paid,
                    COALESCE(cr.carried_balance, 0) as carried_balance,
                    COALESCE(SUM(
                        CASE
                            WHEN sfe.exemption_id IS NOT NULL THEN 0
                            WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') {is_new_guard} THEN 0
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                            ELSE ft.amount
                        END
                    ), 0) - COALESCE(SUM(sf.amount_paid), 0) + COALESCE(cr.carried_balance, 0) as balance
                FROM students s
                CROSS JOIN fee_types ft
                LEFT JOIN student_fee_exemptions sfe ON sfe.student_id = s.student_id AND sfe.fee_type_id = ft.fee_type_id
                LEFT JOIN (
                    SELECT student_id, fee_type_id, COALESCE(SUM(amount_paid), 0) AS amount_paid
                    FROM student_fees
                    GROUP BY student_id, fee_type_id
                ) sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                LEFT JOIN (
                    SELECT student_id, COALESCE(SUM(carried_balance), 0) as carried_balance
                    FROM student_term_fee_rollovers
                    WHERE to_academic_year = %s AND to_term = %s
                    GROUP BY student_id
                ) cr ON cr.student_id = s.student_id
                WHERE s.is_active = 1
                  AND ft.academic_year = %s
                  {term_filter}
                  AND (
                        NOT EXISTS (
                            SELECT 1 FROM fee_type_classes ftc0
                            WHERE ftc0.fee_type_id = ft.fee_type_id
                        )
                        OR EXISTS (
                            SELECT 1
                            FROM fee_type_classes ftc
                            JOIN classes c ON c.class_id = ftc.class_id
                            WHERE ftc.fee_type_id = ft.fee_type_id
                              AND LOWER(c.class_name) = LOWER(s.class)
                              AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                        )
                  )
                  {fee_filter}
                GROUP BY s.student_id, s.student_code, s.first_name, s.last_name, s.class, cr.carried_balance
                ORDER BY s.class, s.last_name, s.first_name
            """

            exec_params = [
                academic_year,  # carried balance subquery: to_academic_year
                term,           # carried balance subquery: to_term
                academic_year   # ft.academic_year
            ]
            if not fee_type_id:
                exec_params.extend([
                    term,           # ft.term
                    academic_year,  # NOT EXISTS subquery: ftx.academic_year
                    term            # NOT EXISTS subquery: ftx.term
                ])
            exec_params.append(academic_year)  # fee_type_classes academic_year filter
            if fee_type_id:
                exec_params.append(fee_type_id)
            results = db.execute_query(query, tuple(exec_params), fetch=True)

            out = []
            for row in results:
                balance = float(row.get('balance') or 0)
                total_fees = float(row.get('total_fees') or 0)
                amount_paid = float(row.get('amount_paid') or 0)
                carried_balance = float(row.get('carried_balance') or 0)
                out.append({
                    'student_id': row.get('student_id'),
                    'student_code': row.get('student_code'),
                    'student_name': row.get('student_name'),
                    'class': row.get('class'),
                    # Keep both legacy and newer field names for compatibility
                    'total_due': total_fees,
                    'total_fees': total_fees,
                    'total_paid': amount_paid,
                    'amount_paid': amount_paid,
                    'carried_balance': carried_balance,
                    'balance': balance
                })
            return out
        except Exception:
            return []

    @staticmethod
    def get_student_balance(student_id: int, academic_year: str = None, fee_type_id: int = None, term: str = None) -> Dict:
        """Get totals for a single student for a term, including carried balance."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        if not term:
            term = config.Config.CURRENT_TERM
        try:
            FinancialManager._ensure_term_rollover_tables()
            # Get student class for tuition overrides
            from database.queries import student_is_new_available
            if student_is_new_available():
                sres = db.execute_query("SELECT class, is_new FROM students WHERE student_id=%s", (student_id,), fetch=True)
            else:
                sres = db.execute_query("SELECT class FROM students WHERE student_id=%s", (student_id,), fetch=True)
            student_class = sres[0]['class'] if sres else ''
            is_new_value = int(sres[0].get('is_new', 1)) if sres else 1

            fee_filter = ""
            term_filter = """
                  AND (
                        ft.term = %s
                        OR ft.term IS NULL
                        OR ft.term = ''
                        OR NOT EXISTS (
                            SELECT 1
                            FROM fee_types ftx
                            WHERE ftx.academic_year = %s
                              AND ftx.term = %s
                        )
                  )
            """
            if fee_type_id:
                fee_filter = "AND ft.fee_type_id = %s"
                # For explicit fee-type filter, do not constrain to current term.
                term_filter = ""

            query = f"""
                SELECT
                    COALESCE(SUM(
                        CASE
                            WHEN sfe.exemption_id IS NOT NULL THEN 0
                            WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') AND %s = 0 THEN 0
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(%s) LIKE '%%nursery%%' OR LOWER(%s) LIKE '%%reception%%') THEN 45000
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                            ELSE ft.amount
                        END
                    ), 0) as total_expected,
                    COALESCE(SUM(sf.amount_paid), 0) as total_paid,
                    COALESCE(cr.carried_balance, 0) as carried_balance
                FROM fee_types ft
                LEFT JOIN student_fee_exemptions sfe ON sfe.fee_type_id = ft.fee_type_id AND sfe.student_id = %s
                LEFT JOIN (
                    SELECT student_id, fee_type_id, COALESCE(SUM(amount_paid), 0) AS amount_paid
                    FROM student_fees
                    GROUP BY student_id, fee_type_id
                ) sf ON sf.fee_type_id = ft.fee_type_id AND sf.student_id = %s
                LEFT JOIN (
                    SELECT student_id, COALESCE(SUM(carried_balance), 0) as carried_balance
                    FROM student_term_fee_rollovers
                    WHERE to_academic_year = %s AND to_term = %s AND student_id = %s
                    GROUP BY student_id
                ) cr ON cr.student_id = %s
                WHERE ft.academic_year = %s
                  {term_filter}
                  AND (
                        NOT EXISTS (
                            SELECT 1 FROM fee_type_classes ftc0
                            WHERE ftc0.fee_type_id = ft.fee_type_id
                        )
                        OR EXISTS (
                            SELECT 1
                            FROM fee_type_classes ftc
                            JOIN classes c ON c.class_id = ftc.class_id
                            WHERE ftc.fee_type_id = ft.fee_type_id
                              AND LOWER(c.class_name) = LOWER(%s)
                              AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                        )
                  )
                  {fee_filter}
            """

            # params for LOWER(class) replacement plus student params
            exec_params = [
                is_new_value,
                student_class,
                student_class,
                student_id,
                student_id,
                academic_year,
                term,
                student_id,
                student_id,
                academic_year,  # ft.academic_year
                student_class,  # fee_type_classes class filter
                academic_year   # fee_type_classes academic_year filter
            ]
            if not fee_type_id:
                exec_params[9:9] = [
                    term,           # ft.term
                    academic_year,  # NOT EXISTS subquery: ftx.academic_year
                    term            # NOT EXISTS subquery: ftx.term
                ]
            if fee_type_id:
                exec_params.append(fee_type_id)
            res = db.execute_query(query, tuple(exec_params), fetch=True)
            row = res[0] if res else {'total_expected': 0, 'total_paid': 0, 'carried_balance': 0}
            total_expected = float(row.get('total_expected') or 0)
            total_paid = float(row.get('total_paid') or 0)
            carried_balance = float(row.get('carried_balance') or 0)
            balance = total_expected - total_paid + carried_balance
            return {
                'student_id': student_id,
                'total_expected': total_expected,
                'total_paid': total_paid,
                'carried_balance': carried_balance,
                'balance': balance
            }
        except Exception:
            return {'student_id': student_id, 'total_expected': 0, 'total_paid': 0, 'carried_balance': 0, 'balance': 0}

    @staticmethod
    def get_collected_by_fee_type(start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """Return totals collected grouped by fee type for a period (wrapper for UI)."""
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

    @staticmethod
    def start_new_term(new_term: str, term_start_date: str = None):
        """Backward-compatible wrapper for centralized term rollover execution."""
        try:
            FinancialManager.execute_term_rollover(
                academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
                from_term=config.Config.CURRENT_TERM,
                to_term=new_term,
                term_start_date=term_start_date
            )
            return True
        except Exception:
            return False
