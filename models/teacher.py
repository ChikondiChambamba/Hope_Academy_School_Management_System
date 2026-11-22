"""
Teacher model and data management
"""
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional, List, Dict, Any
import config
from database.connection import db
from utils.validators import Validators

@dataclass
class Teacher:
    """Teacher data model"""
    
    teacher_id: Optional[int] = None
    teacher_code: str = ""
    first_name: str = ""
    last_name: str = ""
    phone: str = ""
    email: str = ""
    subject_specialization: str = ""
    hire_date: Optional[date] = None
    salary_amount: float = 0.0
    allowance_amount: float = 0.0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize after dataclass creation"""
        if isinstance(self.hire_date, str):
            self.hire_date = datetime.strptime(self.hire_date, '%Y-%m-%d').date()
    
    def validate(self) -> tuple[bool, str]:
        """Validate teacher data"""
        # Check required fields
        required_fields = ['first_name', 'last_name', 'hire_date']
        for field in required_fields:
            value = getattr(self, field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                return False, f"{field.replace('_', ' ').title()} is required"
        
        # Validate teacher code format
        if self.teacher_code and not self.teacher_code.startswith('TCH'):
            return False, "Teacher code must start with 'TCH'"
        
        # Validate email
        if self.email and not Validators.validate_email(self.email):
            return False, "Invalid email format"
        
        # Validate phone
        if self.phone and not Validators.validate_phone(self.phone):
            return False, "Invalid phone number format"
        
        # Validate hire date
        if self.hire_date and self.hire_date > date.today():
            return False, "Hire date cannot be in the future"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save teacher to database"""
        # Coerce hire_date string to date if necessary
        if isinstance(self.hire_date, str):
            try:
                self.hire_date = datetime.strptime(self.hire_date, '%Y-%m-%d').date()
            except Exception:
                pass

        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
            teacher_data = self.to_dict()
            
            if self.teacher_id:  # Update existing
                # Remove timestamps
                teacher_data.pop('created_at', None)
                teacher_data.pop('updated_at', None)
                # Preserve existing teacher_code when updating if none provided
                current_code = self.teacher_code or ''
                new_code = teacher_data.get('teacher_code') or current_code
                if not new_code:
                    # As a last resort, generate a new code
                    new_code = self.generate_teacher_code()

                query = """
                    UPDATE teachers SET 
                    teacher_code = %s, first_name = %s, last_name = %s,
                    phone = %s, email = %s, subject_specialization = %s,
                    hire_date = %s, salary_amount = %s, allowance_amount = %s, is_active = %s
                    WHERE teacher_id = %s
                """
                params = (
                    new_code,
                    teacher_data['first_name'],
                    teacher_data['last_name'],
                    teacher_data['phone'],
                    teacher_data['email'],
                    teacher_data['subject_specialization'],
                    teacher_data['hire_date'],
                    teacher_data['salary_amount'],
                    teacher_data.get('allowance_amount', 0.0),
                    teacher_data['is_active'],
                    self.teacher_id
                )

                db.execute_query(query, params)
                # Update in-memory value
                self.teacher_code = new_code
                return True, "Teacher updated successfully"
                
            else:  # Insert new
                # Generate teacher code if not provided
                if not teacher_data['teacher_code']:
                    teacher_data['teacher_code'] = self.generate_teacher_code()
                
                query = """
                    INSERT INTO teachers 
                    (teacher_code, first_name, last_name, phone, email, 
                     subject_specialization, hire_date, salary_amount, allowance_amount, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    teacher_data['teacher_code'],
                    teacher_data['first_name'],
                    teacher_data['last_name'],
                    teacher_data['phone'],
                    teacher_data['email'],
                    teacher_data['subject_specialization'],
                    teacher_data['hire_date'],
                    teacher_data['salary_amount'],
                    teacher_data.get('allowance_amount', 0.0),
                    teacher_data['is_active']
                )
                
                teacher_id = db.execute_query(query, params)
                self.teacher_id = teacher_id
                return True, f"Teacher added successfully with ID: {teacher_id}"
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def generate_teacher_code(self) -> str:
        """Generate unique teacher code"""
        try:
            # Optionally use random IDs for compatibility with large datasets
            if getattr(config.Config, 'USE_RANDOM_IDS', False):
                import uuid
                return f"TCH{uuid.uuid4().hex[:8].upper()}"

            # Get next teacher number
            query = """
                SELECT MAX(CAST(SUBSTRING(teacher_code, 4) AS UNSIGNED)) as max_num
                FROM teachers 
                WHERE teacher_code LIKE 'TCH%'
            """
            result = db.execute_query(query, fetch=True)
            
            if result and result[0].get('max_num'):
                next_num = result[0]['max_num'] + 1
            else:
                next_num = 101

            return f"TCH{next_num}"
        except:
            # Fallback to timestamp-based code
            timestamp = datetime.now().strftime('%y%m%d%H%M')
            return f"TCH{timestamp}"
    
    def get_classes(self) -> List[Dict]:
        """Get classes taught by this teacher"""
        try:
            query = """
                SELECT 
                    c.class_name,
                    c.room_number,
                    COUNT(sc.student_id) as student_count
                FROM classes c
                LEFT JOIN student_classes sc ON c.class_id = sc.class_id AND sc.academic_year = %s
                WHERE c.teacher_id = %s
                GROUP BY c.class_id, c.class_name, c.room_number
                ORDER BY c.class_name
            """
            return db.execute_query(query, (config.Config.CURRENT_ACADEMIC_YEAR, self.teacher_id), fetch=True)
        except:
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert teacher to dictionary"""
        data = asdict(self)
        
        # Convert dates to strings
        if data['hire_date'] and isinstance(data['hire_date'], date):
            data['hire_date'] = data['hire_date'].isoformat()
        
        # Convert datetimes to strings
        for field in ['created_at', 'updated_at']:
            if data[field] and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Teacher':
        """Create Teacher instance from a query row (extra joined columns are ignored)."""
        from .row_mapping import from_row
        return from_row(cls, data)
    
    @classmethod
    def get_all(cls, active_only: bool = True) -> List['Teacher']:
        """Get all teachers"""
        try:
            query = "SELECT * FROM teachers"
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY last_name, first_name"
            
            results = db.execute_query(query, fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_id(cls, teacher_id: int) -> Optional['Teacher']:
        """Get teacher by ID"""
        try:
            query = "SELECT * FROM teachers WHERE teacher_id = %s"
            result = db.execute_query(query, (teacher_id,), fetch=True)
            if result:
                return cls.from_dict(result[0])
            return None
        except:
            return None
    
    @classmethod
    def search(cls, search_term: str) -> List['Teacher']:
        """Search teachers by name or code"""
        try:
            query = """
                SELECT * FROM teachers 
                WHERE (first_name LIKE %s OR last_name LIKE %s OR teacher_code LIKE %s)
                AND is_active = 1
                ORDER BY last_name, first_name
            """
            search_pattern = f"%{search_term}%"
            results = db.execute_query(query, (search_pattern, search_pattern, search_pattern), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []


class TeacherManager:
    """Manager class for teacher operations"""

    @staticmethod
    def create_teacher(teacher_data: Dict) -> tuple[bool, str, Optional[Teacher]]:
        teacher = Teacher.from_dict(teacher_data)
        success, message = teacher.save()
        return success, message, teacher if success else None

    @staticmethod
    def update_teacher(teacher_id: int, teacher_data: Dict) -> tuple[bool, str]:
        teacher = Teacher.get_by_id(teacher_id)
        if not teacher:
            return False, "Teacher not found"

        for key, value in teacher_data.items():
            if hasattr(teacher, key):
                setattr(teacher, key, value)

        return teacher.save()

    @staticmethod
    def delete_teacher(teacher_id: int) -> tuple[bool, str]:
        teacher = Teacher.get_by_id(teacher_id)
        if not teacher:
            return False, "Teacher not found"

        try:
            query = "UPDATE teachers SET is_active = 0 WHERE teacher_id = %s"
            db.execute_query(query, (teacher_id,))
            return True, "Teacher deactivated successfully"
        except Exception as e:
            return False, f"Database error: {str(e)}"

    @staticmethod
    def permanently_delete_teacher(teacher_id: int) -> tuple[bool, str]:
        """Permanently remove a teacher row from the database."""
        teacher = Teacher.get_by_id(teacher_id)
        if not teacher:
            return False, "Teacher not found"

        try:
            query = "DELETE FROM teachers WHERE teacher_id = %s"
            db.execute_query(query, (teacher_id,))
            return True, "Teacher permanently deleted"
        except Exception as e:
            return False, f"Database error: {str(e)}"
