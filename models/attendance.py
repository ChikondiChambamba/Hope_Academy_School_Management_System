"""
Attendance management models
"""
from dataclasses import dataclass, asdict
from datetime import date, datetime, time
from typing import Optional, List, Dict, Any
import config
from database.connection import db
from database.queries import Queries
from models.student import Student

@dataclass
class Attendance:
    """Attendance record model"""
    
    attendance_id: Optional[int] = None
    student_id: int = 0
    attendance_date: Optional[date] = None
    status: str = "Present"  # Present, Absent, Late, Excused
    check_in_time: Optional[time] = None
    check_out_time: Optional[time] = None
    remarks: str = ""
    recorded_by: str = ""
    created_at: Optional[datetime] = None
    
    # Joined fields
    student_name: str = ""
    class_name: str = ""
    
    def __post_init__(self):
        """Initialize after dataclass creation"""
        if isinstance(self.attendance_date, str):
            self.attendance_date = datetime.strptime(self.attendance_date, '%Y-%m-%d').date()
        if not self.attendance_date:
            self.attendance_date = date.today()
        
        # Parse times if they are strings
        if isinstance(self.check_in_time, str):
            try:
                self.check_in_time = datetime.strptime(self.check_in_time, '%H:%M:%S').time()
            except:
                self.check_in_time = None
        
        if isinstance(self.check_out_time, str):
            try:
                self.check_out_time = datetime.strptime(self.check_out_time, '%H:%M:%S').time()
            except:
                self.check_out_time = None
    
    def validate(self) -> tuple[bool, str]:
        """Validate attendance data"""
        if self.student_id <= 0:
            return False, "Student ID is required"
        
        if not self.attendance_date:
            return False, "Attendance date is required"
        
        if self.attendance_date > date.today():
            return False, "Attendance date cannot be in the future"
        
        valid_statuses = ['Present', 'Absent', 'Late', 'Excused']
        if self.status not in valid_statuses:
            return False, f"Status must be one of: {', '.join(valid_statuses)}"
        
        # Validate times if provided
        if self.check_in_time and self.check_out_time:
            if self.check_out_time < self.check_in_time:
                return False, "Check-out time cannot be before check-in time"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save attendance record to database"""
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
            attendance_data = self.to_dict()
            
            # Check if attendance already exists for this student on this date
            query = """
                SELECT attendance_id FROM attendance 
                WHERE student_id = %s AND attendance_date = %s
            """
            existing = db.execute_query(query, (self.student_id, self.attendance_date), fetch=True)
            
            if existing:  # Update existing
                query = """
                    UPDATE attendance SET 
                    status = %s, check_in_time = %s, check_out_time = %s,
                    remarks = %s, recorded_by = %s
                    WHERE attendance_id = %s
                """
                params = (
                    self.status,
                    self.check_in_time,
                    self.check_out_time,
                    self.remarks,
                    self.recorded_by,
                    existing[0]['attendance_id']
                )
                
                db.execute_query(query, params)
                self.attendance_id = existing[0]['attendance_id']
                return True, "Attendance updated successfully"
                
            else:  # Insert new
                query = """
                    INSERT INTO attendance 
                    (student_id, attendance_date, status, check_in_time, 
                     check_out_time, remarks, recorded_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    self.student_id,
                    self.attendance_date,
                    self.status,
                    self.check_in_time,
                    self.check_out_time,
                    self.remarks,
                    self.recorded_by
                )
                
                self.attendance_id = db.execute_query(query, params)
                return True, "Attendance recorded successfully"
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert attendance to dictionary"""
        data = asdict(self)
        
        # Convert dates to strings
        if data['attendance_date'] and isinstance(data['attendance_date'], date):
            data['attendance_date'] = data['attendance_date'].isoformat()
        
        # Convert times to strings
        if data['check_in_time'] and isinstance(data['check_in_time'], time):
            data['check_in_time'] = data['check_in_time'].strftime('%H:%M:%S')
        
        if data['check_out_time'] and isinstance(data['check_out_time'], time):
            data['check_out_time'] = data['check_out_time'].strftime('%H:%M:%S')
        
        # Convert datetime to string
        if data['created_at'] and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Attendance':
        """Create Attendance instance from a row (joined student columns are mapped)."""
        from .row_mapping import from_row
        return from_row(cls, data)
    
    @classmethod
    def get_by_date(cls, attendance_date: date) -> List['Attendance']:
        """Get attendance records for a specific date"""
        try:
            query = Queries.GET_ATTENDANCE_BY_DATE
            results = db.execute_query(query, (attendance_date,), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_student(cls, student_id: int, start_date: date = None, end_date: date = None) -> List['Attendance']:
        """Get attendance records for a student"""
        try:
            if not start_date:
                start_date = date(date.today().year, 1, 1)
            if not end_date:
                end_date = date.today()
            
            query = """
                SELECT 
                    a.*,
                    s.first_name,
                    s.last_name,
                    s.class
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.student_id = %s
                    AND a.attendance_date BETWEEN %s AND %s
                ORDER BY a.attendance_date DESC
            """
            results = db.execute_query(query, (student_id, start_date, end_date), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_summary_by_date_range(cls, start_date: date, end_date: date) -> Dict:
        """Get attendance summary for date range"""
        try:
            query = Queries.GET_ATTENDANCE_SUMMARY
            results = db.execute_query(query, (start_date, end_date), fetch=True)
            
            # Calculate totals
            total_days = len(results)
            total_students = sum(r['total_students'] for r in results) if results else 0
            total_present = sum(r['present'] for r in results) if results else 0
            
            # Calculate attendance rate
            attendance_rate = (total_present / total_students * 100) if total_students > 0 else 0
            
            return {
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days,
                'total_students': total_students,
                'total_present': total_present,
                'total_absent': sum(r['absent'] for r in results) if results else 0,
                'total_late': sum(r['late'] for r in results) if results else 0,
                'total_excused': sum(r['excused'] for r in results) if results else 0,
                'attendance_rate': round(attendance_rate, 2),
                'daily_summary': results
            }
        except Exception as e:
            print(f"Error getting attendance summary: {e}")
            return {}
    
    @classmethod
    def get_student_attendance_rate(cls, student_id: int, academic_year: str = None) -> float:
        """Calculate attendance rate for a student"""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        
        try:
            # Get start and end dates for academic year
            start_date = date(int(academic_year), 1, 1)
            end_date = date.today()
            
            query = """
                SELECT 
                    COUNT(*) as total_days,
                    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_days
                FROM attendance
                WHERE student_id = %s
                    AND attendance_date BETWEEN %s AND %s
            """
            result = db.execute_query(query, (student_id, start_date, end_date), fetch=True)
            
            if result and result[0]['total_days'] > 0:
                present_days = result[0]['present_days'] or 0
                attendance_rate = (present_days / result[0]['total_days']) * 100
                return round(attendance_rate, 2)
            
            return 0.0
        except:
            return 0.0


class AttendanceManager:
    """Manager for attendance operations"""
    
    @staticmethod
    def record_attendance_for_class(class_name: str, attendance_date: date, 
                                   attendance_data: List[Dict]) -> tuple[bool, str]:
        """Record attendance for entire class"""
        try:
            # Get all students in the class
            students = Student.get_by_class(class_name)
            student_ids = {s.student_id for s in students}
            
            success_count = 0
            error_messages = []
            
            for record in attendance_data:
                student_id = record.get('student_id')
                
                if student_id not in student_ids:
                    error_messages.append(f"Student ID {student_id} not in class {class_name}")
                    continue
                
                attendance = Attendance(
                    student_id=student_id,
                    attendance_date=attendance_date,
                    status=record.get('status', 'Present'),
                    remarks=record.get('remarks', '')
                )
                
                success, message = attendance.save()
                if success:
                    success_count += 1
                else:
                    error_messages.append(f"Student {student_id}: {message}")
            
            total_count = len(attendance_data)
            error_count = len(error_messages)
            
            if error_count == 0:
                return True, f"Attendance recorded for {success_count}/{total_count} students"
            else:
                message = f"Attendance recorded for {success_count}/{total_count} students. Errors: {error_count}"
                if error_messages:
                    message += f"\nFirst error: {error_messages[0]}"
                return False, message
            
        except Exception as e:
            return False, f"Error recording attendance: {str(e)}"
    
    @staticmethod
    def get_daily_attendance_report(attendance_date: date) -> Dict:
        """Generate daily attendance report"""
        try:
            # Get attendance for the day
            attendance_records = Attendance.get_by_date(attendance_date)
            
            # Group by class
            class_summary = {}
            student_details = []
            
            for record in attendance_records:
                class_name = record.class_name
                student_details.append({
                    'student_name': record.student_name,
                    'class': class_name,
                    'status': record.status,
                    'check_in': record.check_in_time,
                    'check_out': record.check_out_time,
                    'remarks': record.remarks
                })
                
                if class_name not in class_summary:
                    class_summary[class_name] = {
                        'total': 0,
                        'present': 0,
                        'absent': 0,
                        'late': 0,
                        'excused': 0
                    }
                
                class_summary[class_name]['total'] += 1
                class_summary[class_name][record.status.lower()] += 1
            
            # Calculate totals
            totals = {
                'total': sum(cs['total'] for cs in class_summary.values()),
                'present': sum(cs['present'] for cs in class_summary.values()),
                'absent': sum(cs['absent'] for cs in class_summary.values()),
                'late': sum(cs['late'] for cs in class_summary.values()),
                'excused': sum(cs['excused'] for cs in class_summary.values())
            }
            
            # Calculate attendance rate
            if totals['total'] > 0:
                attendance_rate = (totals['present'] / totals['total']) * 100
            else:
                attendance_rate = 0
            
            return {
                'date': attendance_date,
                'total_students': totals['total'],
                'present': totals['present'],
                'absent': totals['absent'],
                'late': totals['late'],
                'excused': totals['excused'],
                'attendance_rate': round(attendance_rate, 2),
                'class_summary': class_summary,
                'student_details': student_details
            }
            
        except Exception as e:
            print(f"Error generating daily report: {e}")
            return {}
    
    @staticmethod
    def get_student_attendance_report(student_id: int, start_date: date = None, end_date: date = None) -> Dict:
        """Generate attendance report for a student"""
        try:
            if not start_date:
                start_date = date(date.today().year, 1, 1)
            if not end_date:
                end_date = date.today()
            
            # Get student info
            student = Student.get_by_id(student_id)
            if not student:
                return {}
            
            # Get attendance records
            attendance_records = Attendance.get_by_student(student_id, start_date, end_date)
            
            # Calculate statistics
            total_days = len(attendance_records)
            present_days = sum(1 for r in attendance_records if r.status == 'Present')
            absent_days = sum(1 for r in attendance_records if r.status == 'Absent')
            late_days = sum(1 for r in attendance_records if r.status == 'Late')
            excused_days = sum(1 for r in attendance_records if r.status == 'Excused')
            
            if total_days > 0:
                attendance_rate = (present_days / total_days) * 100
            else:
                attendance_rate = 0
            
            return {
                'student_name': f"{student.first_name} {student.last_name}",
                'student_code': student.student_code,
                'class': student.class_name,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'statistics': {
                    'total_days': total_days,
                    'present_days': present_days,
                    'absent_days': absent_days,
                    'late_days': late_days,
                    'excused_days': excused_days,
                    'attendance_rate': round(attendance_rate, 2)
                },
                'attendance_records': [
                    {
                        'date': record.attendance_date,
                        'status': record.status,
                        'check_in': record.check_in_time,
                        'check_out': record.check_out_time,
                        'remarks': record.remarks
                    }
                    for record in attendance_records
                ]
            }
            
        except Exception as e:
            print(f"Error generating student attendance report: {e}")
            return {}