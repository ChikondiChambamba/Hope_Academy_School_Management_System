"""
Student model and data management
"""
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import config
from database.connection import db
from database.queries import Queries
from utils.validators import Validators

@dataclass
class Student:
    """Student data model"""
    
    student_id: Optional[int] = None
    student_code: str = ""
    first_name: str = ""
    last_name: str = ""
    class_name: str = ""
    birth_date: Optional[date] = None
    parent_name: str = ""
    parent_phone: str = ""
    parent_email: str = ""
    address: str = ""
    enrollment_date: Optional[date] = None
    is_active: bool = True
    is_new: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Computed fields (not stored in database)
    total_paid: float = 0.0
    total_due: float = 0.0
    balance: float = 0.0
    
    def __post_init__(self):
        """Initialize after dataclass creation"""
        if isinstance(self.birth_date, str):
            self.birth_date = datetime.strptime(self.birth_date, '%Y-%m-%d').date()
        if isinstance(self.enrollment_date, str):
            self.enrollment_date = datetime.strptime(self.enrollment_date, '%Y-%m-%d').date()
    
    def validate(self) -> tuple[bool, str]:
        """Validate student data"""
        # Check required fields
        required_fields = ['first_name', 'last_name', 'class_name', 'enrollment_date']
        for field in required_fields:
            value = getattr(self, field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                return False, f"{field.replace('_', ' ').title()} is required"
        
        # Validate student code format
        if self.student_code and not self.student_code.startswith('STU'):
            return False, "Student code must start with 'STU'"
        
        # Validate dates
        if self.birth_date and self.birth_date > date.today():
            return False, "Birth date cannot be in the future"
        
        if self.enrollment_date and self.enrollment_date > date.today():
            return False, "Enrollment date cannot be in the future"
        
        # Validate phone number
        if self.parent_phone and not Validators.validate_phone(self.parent_phone):
            return False, "Invalid phone number format"

        # Validate parent email
        if self.parent_email and not Validators.validate_email(self.parent_email):
            return False, "Invalid parent email format"
        
        # Check age
        if self.birth_date:
            age = (date.today() - self.birth_date).days // 365
            if age < config.Config.VALIDATION['min_student_age']:
                return False, f"Student must be at least {config.Config.VALIDATION['min_student_age']} years old"
            if age > config.Config.VALIDATION['max_student_age']:
                return False, f"Student cannot be older than {config.Config.VALIDATION['max_student_age']} years"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save student to database"""
        # Coerce date strings to date objects if needed (handles dialog input)
        if isinstance(self.birth_date, str):
            try:
                self.birth_date = datetime.strptime(self.birth_date, '%Y-%m-%d').date()
            except Exception:
                pass

        if isinstance(self.enrollment_date, str):
            try:
                self.enrollment_date = datetime.strptime(self.enrollment_date, '%Y-%m-%d').date()
            except Exception:
                pass

        # Validate before saving
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
            from utils.audit_logger import log_student_action
            
            # Prepare data for database
            student_data = self.to_dict()
            
            if self.student_id:  # Update existing student
                # Remove computed fields and timestamps
                for field in ['total_paid', 'total_due', 'balance', 'created_at', 'updated_at']:
                    student_data.pop(field, None)
                
                query = """
                    UPDATE students SET 
                    student_code = %s, first_name = %s, last_name = %s, 
                    class = %s, birth_date = %s, parent_name = %s, 
                    parent_phone = %s, parent_email = %s, address = %s, enrollment_date = %s,
                    is_active = %s, is_new = %s
                    WHERE student_id = %s
                """
                params = (
                    student_data['student_code'],
                    student_data['first_name'],
                    student_data['last_name'],
                    student_data['class_name'],
                    student_data['birth_date'],
                    student_data['parent_name'],
                    student_data['parent_phone'],
                    student_data.get('parent_email'),
                    student_data['address'],
                    student_data['enrollment_date'],
                    student_data['is_active'],
                    student_data.get('is_new', True),
                    self.student_id
                )
                
                db.execute_query(query, params)
                
                # Log the update action
                log_student_action('UPDATE', self.student_id, 'Student updated')
                
                return True, "Student updated successfully"
                
            else:  # Insert new student
                # Generate student code if not provided
                if not student_data['student_code']:
                    student_data['student_code'] = self.generate_student_code()
                # Prevent duplicate active student (same first/last name in same class)
                try:
                    dup_query = "SELECT COUNT(*) as cnt FROM students WHERE LOWER(first_name)=LOWER(%s) AND LOWER(last_name)=LOWER(%s) AND class=%s AND is_active = 1"
                    dup_res = db.execute_query(dup_query, (student_data['first_name'], student_data['last_name'], student_data['class_name']), fetch=True)
                    if dup_res and dup_res[0].get('cnt', 0) > 0:
                        return False, "A student with the same name already exists in this class"
                except Exception:
                    # On error, continue to attempt insert (do not block due to dup check failure)
                    pass

                query = """
                    INSERT INTO students 
                    (student_code, first_name, last_name, class, birth_date, 
                     parent_name, parent_phone, parent_email, address, enrollment_date, is_active, is_new)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    student_data['student_code'],
                    student_data['first_name'],
                    student_data['last_name'],
                    student_data['class_name'],
                    student_data['birth_date'],
                    student_data['parent_name'],
                    student_data['parent_phone'],
                    student_data.get('parent_email'),
                    student_data['address'],
                    student_data['enrollment_date'],
                    student_data['is_active'],
                    student_data.get('is_new', True)
                )
                
                student_id = db.execute_query(query, params)
                self.student_id = student_id
                
                # Log the creation action
                log_student_action('CREATE', student_id, f'Student {student_data["first_name"]} {student_data["last_name"]} created')
                
                return True, f"Student added successfully with ID: {student_id}"
                
        except Exception as e:
            from utils.audit_logger import log_student_action
            # Log the failed action
            log_student_action('CREATE' if not self.student_id else 'UPDATE', self.student_id, f'Error: {str(e)}', 'FAILED')
            return False, f"Database error: {str(e)}"
    
    def delete(self) -> tuple[bool, str]:
        """Hard delete student and cascade-delete related records."""
        if not self.student_id:
            return False, "Student ID is required"

        try:
            # Deleting the student row will cascade to student_fees, attendance, student_classes
            query = "DELETE FROM students WHERE student_id = %s"
            db.execute_query(query, (self.student_id,))
            return True, "Student deleted successfully"
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def generate_student_code(self) -> str:
        """Generate unique student code"""
        try:
            # Optionally use random IDs for compatibility with large datasets
            if getattr(config.Config, 'USE_RANDOM_IDS', False):
                import uuid
                return f"STU{uuid.uuid4().hex[:8].upper()}"

            # Get next sequential student number
            query = """
                SELECT MAX(CAST(SUBSTRING(student_code, 4) AS UNSIGNED)) as max_num
                FROM students 
                WHERE student_code LIKE 'STU%'
            """
            result = db.execute_query(query, fetch=True)

            if result and result[0].get('max_num'):
                next_num = result[0]['max_num'] + 1
            else:
                next_num = 1001

            return f"STU{next_num}"
        except:
            # Fallback to timestamp-based code
            timestamp = datetime.now().strftime('%y%m%d%H%M')
            return f"STU{timestamp}"
    
    def calculate_balance(self) -> float:
        """Calculate student's fee balance"""
        try:
            from database.queries import get_student_by_id_query
            query = get_student_by_id_query()
            result = db.execute_query(
                query,
                (config.Config.CURRENT_ACADEMIC_YEAR, self.student_id, config.Config.CURRENT_ACADEMIC_YEAR),
                fetch=True
            )
            
            if result:
                self.total_paid = float(result[0]['total_paid'])
                self.total_due = float(result[0]['total_due'])
                self.balance = float(result[0]['balance'])
                return self.balance
            return 0.0
        except:
            return 0.0
    
    def get_fee_details(self) -> List[Dict]:
        """Get detailed fee information for student"""
        try:
            from database.queries import get_student_fee_details_query
            query = get_student_fee_details_query()
            return db.execute_query(
                query,
                (
                    self.student_id,
                    config.Config.CURRENT_ACADEMIC_YEAR,
                    config.Config.CURRENT_ACADEMIC_YEAR,
                    config.Config.CURRENT_TERM,
                    config.Config.CURRENT_ACADEMIC_YEAR,
                    config.Config.CURRENT_TERM
                ),
                fetch=True
            )
        except:
            return []
    
    def get_attendance(self, start_date: date, end_date: date) -> List[Dict]:
        """Get attendance records for date range"""
        try:
            query = """
                SELECT 
                    attendance_date,
                    status,
                    remarks
                FROM attendance
                WHERE student_id = %s
                    AND attendance_date BETWEEN %s AND %s
                ORDER BY attendance_date DESC
            """
            return db.execute_query(query, (self.student_id, start_date, end_date), fetch=True)
        except:
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert student to dictionary"""
        data = asdict(self)
        
        # Convert dates to strings for JSON serialization
        for field in ['birth_date', 'enrollment_date']:
            if data[field] and isinstance(data[field], date):
                data[field] = data[field].isoformat()
        
        # Convert datetimes to strings
        for field in ['created_at', 'updated_at']:
            if data[field] and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Student':
        """Create Student instance from dictionary"""
        from .row_mapping import from_row
        return from_row(cls, data)   # maps the `class` column to class_name
    
    @classmethod
    def _apply_financial_totals(cls, students: List['Student'], academic_year: str = None) -> List['Student']:
        """Attach total_due/total_paid/balance from FinancialManager for consistency across UIs."""
        if not students:
            return students
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        try:
            from models.finance import FinancialManager
            balances = FinancialManager.get_student_balances(
                academic_year=academic_year,
                term=config.Config.CURRENT_TERM
            )
            bal_map = {int(r.get('student_id')): r for r in (balances or []) if r.get('student_id') is not None}
            for s in students:
                row = bal_map.get(int(s.student_id)) if s.student_id is not None else None
                if not row:
                    continue
                s.total_due = float(row.get('opening_balance') or 0)
                s.total_paid = float(row.get('total_paid') or 0)
                s.balance = float(row.get('balance') or 0)
            return students
        except Exception:
            return students

    @classmethod
    def get_all(cls, academic_year: str = None, active_only: bool = True) -> List['Student']:
        """Get all students; by default only active students unless `active_only=False`."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR

        try:
            if active_only:
                from database.queries import get_all_students_query
                query = get_all_students_query()
                results = db.execute_query(query, (academic_year, academic_year), fetch=True)
            else:
                # Similar to GET_ALL_STUDENTS but include inactive rows
                query = """
                    SELECT s.*, 
                           COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
                           COALESCE(SUM(ft.amount), 0) AS total_due,
                           COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) AS balance
                    FROM students s
                    LEFT JOIN student_fees sf ON s.student_id = sf.student_id
                    LEFT JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id AND ft.academic_year = %s
                    GROUP BY s.student_id
                    ORDER BY s.last_name, s.first_name
                """
                results = db.execute_query(query, (academic_year,), fetch=True)

            students = [cls.from_dict(row) for row in results]
            return cls._apply_financial_totals(students, academic_year)
        except:
            return []
    
    @classmethod
    def get_by_id(cls, student_id: int) -> Optional['Student']:
        """Get student by ID"""
        try:
            from database.queries import get_student_by_id_query
            query = get_student_by_id_query()
            result = db.execute_query(
                query,
                (config.Config.CURRENT_ACADEMIC_YEAR, student_id, config.Config.CURRENT_ACADEMIC_YEAR),
                fetch=True
            )
            if result:
                return cls.from_dict(result[0])
            return None
        except:
            return None
    
    @classmethod
    def search(cls, search_term: str, academic_year: str = None, active_only: bool = True) -> List['Student']:
        """Search students by name or code; optionally include inactive records."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR

        try:
            search_pattern = f"%{search_term}%"
            if active_only:
                from database.queries import search_students_query
                query = search_students_query()
                params = (academic_year, search_pattern, search_pattern, search_pattern, academic_year)
            else:
                # Variant that doesn't filter on is_active
                query = """
                    SELECT s.*, 
                           COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
                           COALESCE(SUM(ft.amount), 0) AS total_due,
                           COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) AS balance
                    FROM students s
                    LEFT JOIN student_fees sf ON s.student_id = sf.student_id
                    LEFT JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id AND ft.academic_year = %s
                    WHERE (s.first_name LIKE %s OR s.last_name LIKE %s OR s.student_code LIKE %s)
                    GROUP BY s.student_id
                    ORDER BY s.last_name, s.first_name
                """
                params = (academic_year, search_pattern, search_pattern, search_pattern)

            results = db.execute_query(query, params, fetch=True)
            students = [cls.from_dict(row) for row in results]
            return cls._apply_financial_totals(students, academic_year)
        except:
            return []
    
    @classmethod
    def get_by_class(cls, class_name: str, academic_year: str = None, active_only: bool = True) -> List['Student']:
        """Get students in a specific class; optionally include inactive."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR

        try:
            if active_only:
                query = Queries.get_students_by_class(class_name)
                results = db.execute_query(query, (academic_year, class_name), fetch=True)
            else:
                query = """
                    SELECT s.*, 
                           COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
                           COALESCE(SUM(ft.amount), 0) AS total_due,
                           COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) AS balance
                    FROM students s
                    LEFT JOIN student_fees sf ON s.student_id = sf.student_id
                    LEFT JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id AND ft.academic_year = %s
                    WHERE s.class = %s
                    GROUP BY s.student_id
                    ORDER BY s.last_name, s.first_name
                """
                results = db.execute_query(query, (academic_year, class_name), fetch=True)

            students = [cls.from_dict(row) for row in results]
            return cls._apply_financial_totals(students, academic_year)
        except:
            return []
    
    @classmethod
    def get_total_count(cls) -> int:
        """Get total number of active students"""
        try:
            query = "SELECT COUNT(*) as count FROM students WHERE is_active = 1"
            result = db.execute_query(query, fetch=True)
            return result[0]['count'] if result else 0
        except:
            return 0


class StudentManager:
    """Manager class for student operations"""
    
    @staticmethod
    def create_student(student_data: Dict) -> tuple[bool, str, Optional[Student]]:
        """Create a new student"""
        student = Student.from_dict(student_data)
        success, message = student.save()
        return success, message, student if success else None
    
    @staticmethod
    def update_student(student_id: int, student_data: Dict) -> tuple[bool, str]:
        """Update existing student"""
        student = Student.get_by_id(student_id)
        if not student:
            return False, "Student not found"
        
        # Update student attributes
        for key, value in student_data.items():
            if hasattr(student, key):
                setattr(student, key, value)
        
        return student.save()
    
    @staticmethod
    def delete_student(student_id: int) -> tuple[bool, str]:
        """Delete (deactivate) student"""
        student = Student.get_by_id(student_id)
        if not student:
            return False, "Student not found"
        
        return student.delete()
    
    @staticmethod
    def get_student_financial_summary(student_id: int) -> Dict:
        """Get financial summary for student from the centralized finance engine."""
        from models.finance import FinancialManager
        return FinancialManager.get_student_financial_snapshot(
            student_id,
            academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
            term=config.Config.CURRENT_TERM
        )
    
    @staticmethod
    def get_payment_history(student_id: int) -> List[Dict]:
        """Get payment history for student"""
        from models.finance import FinancialManager
        return FinancialManager.get_student_payment_history(student_id)
    
    @staticmethod
    def record_payment(student_id: int, fee_type_id: int, amount: float, 
                      payment_date: date, payment_method: str = 'Cash', 
                      receipt_number: str = None) -> tuple[bool, str]:
        """Record fee payment for student"""
        try:
            # Use FeePayment model to enforce exemption logic and receipt generation
            from models.finance import FeePayment
            payment = FeePayment(
                student_id=student_id,
                fee_type_id=fee_type_id,
                amount_paid=amount,
                payment_date=payment_date,
                payment_method=payment_method,
                receipt_number=receipt_number or ""
            )
            return payment.save()
        except Exception as e:
            return False, f"Database error: {str(e)}"
