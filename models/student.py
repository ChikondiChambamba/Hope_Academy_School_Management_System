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
    address: str = ""
    enrollment_date: Optional[date] = None
    is_active: bool = True
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
        # Validate before saving
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
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
                    parent_phone = %s, address = %s, enrollment_date = %s,
                    is_active = %s
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
                    student_data['address'],
                    student_data['enrollment_date'],
                    student_data['is_active'],
                    self.student_id
                )
                
                db.execute_query(query, params)
                return True, "Student updated successfully"
                
            else:  # Insert new student
                # Generate student code if not provided
                if not student_data['student_code']:
                    student_data['student_code'] = self.generate_student_code()
                
                query = """
                    INSERT INTO students 
                    (student_code, first_name, last_name, class, birth_date, 
                     parent_name, parent_phone, address, enrollment_date, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    student_data['student_code'],
                    student_data['first_name'],
                    student_data['last_name'],
                    student_data['class_name'],
                    student_data['birth_date'],
                    student_data['parent_name'],
                    student_data['parent_phone'],
                    student_data['address'],
                    student_data['enrollment_date'],
                    student_data['is_active']
                )
                
                student_id = db.execute_query(query, params)
                self.student_id = student_id
                return True, f"Student added successfully with ID: {student_id}"
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def delete(self) -> tuple[bool, str]:
        """Soft delete student (set is_active to False)"""
        if not self.student_id:
            return False, "Student ID is required"
        
        try:
            query = "UPDATE students SET is_active = 0 WHERE student_id = %s"
            db.execute_query(query, (self.student_id,))
            self.is_active = False
            return True, "Student deactivated successfully"
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def generate_student_code(self) -> str:
        """Generate unique student code"""
        try:
            # Get current year
            current_year = date.today().year % 100
            
            # Get next student number
            query = """
                SELECT MAX(CAST(SUBSTRING(student_code, 4) AS UNSIGNED)) as max_num
                FROM students 
                WHERE student_code LIKE 'STU%'
            """
            result = db.execute_query(query, fetch=True)
            
            if result and result[0]['max_num']:
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
            query = Queries.GET_STUDENT_BY_ID
            result = db.execute_query(query, (config.Config.CURRENT_ACADEMIC_YEAR, self.student_id), fetch=True)
            
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
            query = Queries.GET_STUDENT_FEE_DETAILS
            return db.execute_query(query, (self.student_id, config.Config.CURRENT_ACADEMIC_YEAR), fetch=True)
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
        # Handle database field name differences
        if 'class' in data:
            data['class_name'] = data.pop('class')
        
        # Handle None values
        for key, value in data.items():
            if value is None and key in ['birth_date', 'enrollment_date']:
                data[key] = None
        
        return cls(**data)
    
    @classmethod
    def get_all(cls, academic_year: str = None) -> List['Student']:
        """Get all active students"""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        
        try:
            query = Queries.GET_ALL_STUDENTS
            results = db.execute_query(query, (academic_year,), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_id(cls, student_id: int) -> Optional['Student']:
        """Get student by ID"""
        try:
            query = Queries.GET_STUDENT_BY_ID
            result = db.execute_query(query, (config.Config.CURRENT_ACADEMIC_YEAR, student_id), fetch=True)
            if result:
                return cls.from_dict(result[0])
            return None
        except:
            return None
    
    @classmethod
    def search(cls, search_term: str, academic_year: str = None) -> List['Student']:
        """Search students by name or code"""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        
        try:
            query = Queries.SEARCH_STUDENTS
            search_pattern = f"%{search_term}%"
            results = db.execute_query(query, (academic_year, search_pattern, search_pattern, search_pattern), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_class(cls, class_name: str, academic_year: str = None) -> List['Student']:
        """Get students in a specific class"""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        
        try:
            query = Queries.get_students_by_class(class_name)
            results = db.execute_query(query, (academic_year, class_name), fetch=True)
            return [cls.from_dict(row) for row in results]
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
        """Get financial summary for student"""
        student = Student.get_by_id(student_id)
        if not student:
            return {}
        
        fee_details = student.get_fee_details()
        
        summary = {
            'student_name': f"{student.first_name} {student.last_name}",
            'student_code': student.student_code,
            'class': student.class_name,
            'total_due': student.total_due,
            'total_paid': student.total_paid,
            'balance': student.balance,
            'fee_details': fee_details,
            'payment_history': StudentManager.get_payment_history(student_id)
        }
        
        return summary
    
    @staticmethod
    def get_payment_history(student_id: int) -> List[Dict]:
        """Get payment history for student"""
        try:
            query = """
                SELECT 
                    sf.payment_date,
                    ft.fee_name,
                    sf.amount_paid,
                    sf.payment_method,
                    sf.receipt_number
                FROM student_fees sf
                JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
                WHERE sf.student_id = %s
                ORDER BY sf.payment_date DESC
            """
            return db.execute_query(query, (student_id,), fetch=True)
        except:
            return []
    
    @staticmethod
    def record_payment(student_id: int, fee_type_id: int, amount: float, 
                      payment_date: date, payment_method: str = 'Cash', 
                      receipt_number: str = None) -> tuple[bool, str]:
        """Record fee payment for student"""
        try:
            # Check if student exists
            student = Student.get_by_id(student_id)
            if not student:
                return False, "Student not found"
            
            # Check if fee type exists
            query = "SELECT fee_name, amount FROM fee_types WHERE fee_type_id = %s"
            result = db.execute_query(query, (fee_type_id,), fetch=True)
            if not result:
                return False, "Fee type not found"
            
            # Insert payment
            query = """
                INSERT INTO student_fees 
                (student_id, fee_type_id, amount_paid, payment_date, payment_method, receipt_number)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (student_id, fee_type_id, amount, payment_date, payment_method, receipt_number)
            
            db.execute_query(query, params)
            return True, "Payment recorded successfully"
            
        except Exception as e:
            return False, f"Database error: {str(e)}"