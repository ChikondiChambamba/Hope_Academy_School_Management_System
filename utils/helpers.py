"""
Helper functions and utilities
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
import config
from database.connection import db

def setup_logging():
    """Setup application logging"""
    log_file = config.Config.get_log_file()
    
    # Create logs directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger

def check_database_connection() -> bool:
    """Check if database connection is available"""
    try:
        return db.test_connection()
    except:
        return False

def format_currency(amount: float) -> str:
    """Format amount as currency"""
    try:
        symbol = getattr(config.Config, 'CURRENCY_SYMBOL', '$')
        return f"{symbol}{amount:,.2f}"
    except:
        symbol = getattr(config.Config, 'CURRENCY_SYMBOL', '$')
        return f"{symbol}{amount}"


def parse_currency(value: str) -> float:
    """Parse a formatted currency string into a float.

    Handles the configured currency symbol and common separators.
    Returns 0.0 for empty or unparsable values.
    """
    try:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value)
        symbol = getattr(config.Config, 'CURRENCY_SYMBOL', '$').strip()
        if symbol and symbol in s:
            s = s.replace(symbol, '')
        # remove common punctuation
        s = s.replace(',', '').strip()
        # remove any other non-numeric characters (like currency names, symbols)
        import re
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
        if m:
            return float(m.group(0))
        return 0.0
    except:
        return 0.0

def format_date(date_obj: Any) -> str:
    """Format date object to string"""
    if isinstance(date_obj, (date, datetime)):
        return date_obj.strftime(config.Config.FILES['date_format'])
    elif isinstance(date_obj, str):
        return date_obj
    else:
        return str(date_obj)

def parse_date(date_str: str) -> Optional[date]:
    """Parse date string to date object"""
    try:
        return datetime.strptime(date_str, config.Config.FILES['date_format']).date()
    except:
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return None

def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date"""
    today = date.today()
    age = today.year - birth_date.year
    # Adjust if birthday hasn't occurred this year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age

def generate_student_code(class_name: str) -> str:
    """Generate student code based on class"""
    try:
        # Get class prefix (e.g., "G1A" for Grade 1A)
        if class_name:
            # Extract grade and section
            parts = class_name.split()
            if len(parts) >= 2:
                grade = parts[1][0]  # First character of grade
                section = parts[1][-1] if len(parts[1]) > 1 else 'A'
                prefix = f"STU{grade}{section}"
            else:
                prefix = "STU"
        else:
            prefix = "STU"
        
        # Get next sequence number
        query = """
            SELECT MAX(CAST(SUBSTRING(student_code, 6) AS UNSIGNED)) as max_num
            FROM students 
            WHERE student_code LIKE %s
        """
        pattern = f"{prefix}%"
        result = db.execute_query(query, (pattern,), fetch=True)
        
        if result and result[0]['max_num']:
            next_num = result[0]['max_num'] + 1
        else:
            next_num = 1
        
        return f"{prefix}{next_num:03d}"
        
    except:
        # Fallback
        timestamp = datetime.now().strftime('%y%m%d%H%M')
        return f"STU{timestamp}"

def validate_email(email: str) -> bool:
    """Validate email address"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) if email else True

def validate_phone(phone: str) -> bool:
    """Validate phone number"""
    import re
    # Remove spaces and special characters
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    # Check if it's all digits and has reasonable length
    return phone.isdigit() and 10 <= len(phone) <= 15

def get_academic_year_dates(academic_year: str = None):
    """Get start and end dates for academic year"""
    if not academic_year:
        academic_year = config.Config.CURRENT_ACADEMIC_YEAR
    
    year = int(academic_year)
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    return start_date, end_date

def get_term_dates(term: str, academic_year: str = None):
    """Get start and end dates for a term"""
    if not academic_year:
        academic_year = config.Config.CURRENT_ACADEMIC_YEAR
    
    year = int(academic_year)
    
    # Define term dates (adjust based on your school calendar)
    term_dates = {
        'Term 1': (date(year, 1, 15), date(year, 4, 15)),
        'Term 2': (date(year, 5, 1), date(year, 8, 15)),
        'Term 3': (date(year, 9, 1), date(year, 11, 30))
    }
    
    return term_dates.get(term, (date(year, 1, 1), date(year, 12, 31)))

def get_current_term() -> str:
    """Get current term based on date"""
    today = date.today()
    
    # Check which term we're in
    for term in config.Config.TERMS:
        start_date, end_date = get_term_dates(term, str(today.year))
        if start_date <= today <= end_date:
            return term
    
    return config.Config.CURRENT_TERM

def calculate_days_until(date_obj: date) -> int:
    """Calculate days until a date"""
    today = date.today()
    return (date_obj - today).days

def get_upcoming_events(days_ahead: int = 30) -> List[Dict]:
    """Get upcoming events (birthdays, fee due dates, etc.)"""
    events = []
    today = date.today()
    future_date = today + timedelta(days=days_ahead)
    
    try:
        # Get upcoming birthdays
        query = """
            SELECT 
                student_id,
                CONCAT(first_name, ' ', last_name) as student_name,
                class,
                birth_date
            FROM students
            WHERE is_active = 1
                AND DATE_FORMAT(birth_date, '%m-%d') BETWEEN %s AND %s
            ORDER BY DATE_FORMAT(birth_date, '%m-%d')
        """
        
        start_mmdd = today.strftime('%m-%d')
        end_mmdd = future_date.strftime('%m-%d')
        
        birthdays = db.execute_query(query, (start_mmdd, end_mmdd), fetch=True)
        
        for bday in birthdays:
            # Calculate next birthday
            birth_date = parse_date(bday['birth_date'])
            next_birthday = date(today.year, birth_date.month, birth_date.day)
            if next_birthday < today:
                next_birthday = date(today.year + 1, birth_date.month, birth_date.day)
            
            days_until = (next_birthday - today).days
            
            events.append({
                'type': 'birthday',
                'date': next_birthday,
                'days_until': days_until,
                'title': f"{bday['student_name']}'s Birthday",
                'description': f"Class: {bday['class']}",
                'priority': 'low'
            })
        
        # Get upcoming fee due dates (simplified - using end of current term)
        current_term = get_current_term()
        _, term_end_date = get_term_dates(current_term, str(today.year))
        
        if today <= term_end_date <= future_date:
            days_until = (term_end_date - today).days
            events.append({
                'type': 'fee_due',
                'date': term_end_date,
                'days_until': days_until,
                'title': 'Term Fees Due',
                'description': f'{current_term} fees due date',
                'priority': 'high'
            })
        
        # Sort by date
        events.sort(key=lambda x: x['date'])
        
    except Exception as e:
        print(f"Error getting upcoming events: {e}")
    
    return events

def run_database_maintenance() -> tuple:
    """Check the database for damage and tidy it up. Never deletes records.

    Returns (ok, message).
    """
    try:
        if not db.integrity_ok():
            return False, ("The database reported a problem. Restore the most recent backup "
                           "(File > Restore Database) and contact support.")
        db.optimize()
        return True, "The database was checked and is in good order."
    except Exception as e:
        return False, f"Maintenance could not be completed: {e}"

def export_table_to_csv(table_name: str, output_file: str) -> bool:
    """Export database table to CSV file"""
    try:
        import csv
        
        # Get data from table
        query = f"SELECT * FROM {table_name}"
        data = db.execute_query(query, fetch=True)
        
        if not data:
            return False
        
        # Get column names
        if data:
            columns = data[0].keys()
            
            # Write to CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=columns)
                writer.writeheader()
                writer.writerows(data)
            
            return True
        
        return False
        
    except Exception as e:
        print(f"Error exporting table {table_name}: {e}")
        return False

def import_table_from_csv(table_name: str, input_file: str) -> bool:
    """Import data from CSV to database table"""
    try:
        import csv
        
        # Read CSV file
        with open(input_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            data = list(reader)
        
        if not data:
            return False
        
        # Get column names from CSV
        columns = data[0].keys()
        
        # Build INSERT query
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
        # Prepare data for insertion
        values_list = []
        for row in data:
            values = []
            for col in columns:
                value = row[col]
                if value == '':
                    value = None
                values.append(value)
            values_list.append(tuple(values))
        
        # Execute bulk insert
        db.execute_many(query, values_list)
        
        return True
        
    except Exception as e:
        print(f"Error importing table {table_name}: {e}")
        return False

def get_system_info() -> Dict:
    """Get system information"""
    import platform
    import psutil
    
    info = {
        'application': {
            'name': config.Config.APP_NAME,
            'version': config.Config.VERSION,
            'author': config.Config.AUTHOR
        },
        'system': {
            'os': platform.system(),
            'os_version': platform.version(),
            'python_version': platform.python_version(),
            'processor': platform.processor()
        },
        'resources': {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        },
        'database': {
            'host': config.Config.DB_CONFIG['host'],
            'name': config.Config.DB_CONFIG['database'],
            'user': config.Config.DB_CONFIG['user']
        }
    }
    
    return info

def backup_configuration():
    """Backup configuration files"""
    import shutil
    from datetime import datetime
    
    backup_dir = config.Config.PATHS['backups'] / 'config_backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Backup config.py
    config_file = config.Config.RESOURCE_DIR / 'config.py'
    if config_file.exists():
        backup_file = backup_dir / f'config_{timestamp}.py'
        shutil.copy2(config_file, backup_file)
        print(f"Config backed up to: {backup_file}")
    
    # Backup database configuration separately
    db_config = {
        'database': config.Config.DB_CONFIG
    }
    
    import json
    db_config_file = backup_dir / f'db_config_{timestamp}.json'
    with open(db_config_file, 'w') as f:
        json.dump(db_config, f, indent=2)
    
    return True
