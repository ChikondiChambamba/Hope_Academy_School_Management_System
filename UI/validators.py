"""
Input validation and formatting for UI components
"""
import re
from datetime import datetime, date, timedelta
from tkinter import messagebox
import tkinter as tk
from typing import Tuple, Optional, List, Dict, Any
import config

class InputValidator:
    """Input validation for various data types"""
    
    @staticmethod
    def validate_name(name: str, field_name: str = "Name") -> Tuple[bool, str]:
        """Validate person name"""
        if not name or not name.strip():
            return False, f"{field_name} is required"
        
        name = name.strip()
        
        # Check minimum length
        if len(name) < 2:
            return False, f"{field_name} must be at least 2 characters"
        
        # Check maximum length
        if len(name) > 50:
            return False, f"{field_name} cannot exceed 50 characters"
        
        # Check for invalid characters (allow letters, spaces, hyphens, and apostrophes)
        if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s\-\'\.]+$", name):
            return False, f"{field_name} can only contain letters, spaces, hyphens, and apostrophes"
        
        # Check for consecutive special characters
        if re.search(r"[\-\'\s]{2,}", name):
            return False, f"{field_name} cannot have consecutive special characters or spaces"
        
        # Check for valid name format (must start and end with letter)
        if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ]", name) or not re.match(r".*[A-Za-zÀ-ÖØ-öø-ÿ]$", name):
            return False, f"{field_name} must start and end with a letter"
        
        return True, ""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email address"""
        if not email or not email.strip():
            return True, ""  # Email is optional
        
        email = email.strip().lower()
        
        # Check length
        if len(email) > 100:
            return False, "Email cannot exceed 100 characters"
        
        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False, "Invalid email format. Example: user@example.com"
        
        # Check for consecutive dots
        if '..' in email:
            return False, "Email cannot contain consecutive dots"
        
        # Check for invalid characters at start/end
        if email.startswith('.') or email.endswith('.'):
            return False, "Email cannot start or end with a dot"
        
        return True, ""
    
    @staticmethod
    def validate_phone(phone: str, country_code: str = "+255") -> Tuple[bool, str]:
        """Validate phone number (Tanzania format by default)"""
        if not phone or not phone.strip():
            return True, ""  # Phone is optional
        
        phone = phone.strip()
        
        # Remove spaces, hyphens, parentheses
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Check if it's all digits (with optional + at start)
        if not re.match(r'^\+?\d+$', phone_clean):
            return False, "Phone number can only contain digits, spaces, hyphens, parentheses, and +"
        
        # Check length (international format: +255712345678)
        if phone_clean.startswith('+'):
            # International format
            if not phone_clean.startswith('+255'):
                return False, "Country code must be +255 for Tanzania"
            if len(phone_clean) != 13:
                return False, "International format: +255 followed by 9 digits"
        else:
            # Local format (starting with 0)
            if not phone_clean.startswith('0'):
                return False, "Local numbers must start with 0"
            if len(phone_clean) != 10:
                return False, "Local format: 10 digits (0XXXXXXXXX)"
            
            # Convert to international format for validation
            phone_clean = '+255' + phone_clean[1:]
        
        # Check operator code (Tanzania operators: 71, 74, 75, 76, 77, 78, 79)
        operator_code = phone_clean[4:6]
        valid_operators = ['71', '74', '75', '76', '77', '78', '79']
        
        if operator_code not in valid_operators:
            return False, "Invalid mobile operator code. Must be one of: " + ", ".join(valid_operators)
        
        return True, ""
    
    @staticmethod
    def validate_date(date_str: str, field_name: str = "Date", 
                     min_date: Optional[date] = None, 
                     max_date: Optional[date] = None) -> Tuple[bool, str]:
        """Validate date string"""
        if not date_str or not date_str.strip():
            return False, f"{field_name} is required"
        
        date_str = date_str.strip()
        
        # Check format YYYY-MM-DD
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False, f"{field_name} must be in format YYYY-MM-DD"
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if date is valid (e.g., not 2023-02-30)
            if date_obj.strftime('%Y-%m-%d') != date_str:
                return False, f"Invalid {field_name}"
            
            # Check minimum date
            if min_date and date_obj < min_date:
                return False, f"{field_name} cannot be before {min_date.strftime('%Y-%m-%d')}"
            
            # Check maximum date
            if max_date and date_obj > max_date:
                return False, f"{field_name} cannot be after {max_date.strftime('%Y-%m-%d')}"
            
            return True, ""
            
        except ValueError:
            return False, f"Invalid {field_name}"
    
    @staticmethod
    def validate_future_date(date_str: str, field_name: str = "Date", 
                           days_future: int = 365) -> Tuple[bool, str]:
        """Validate that date is not too far in the future"""
        is_valid, message = InputValidator.validate_date(date_str, field_name)
        if not is_valid:
            return False, message
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = date.today()
            max_future_date = today + timedelta(days=days_future)
            
            if date_obj > max_future_date:
                return False, f"{field_name} cannot be more than {days_future} days in the future"
            
            return True, ""
        except:
            return False, f"Invalid {field_name}"
    
    @staticmethod
    def validate_past_date(date_str: str, field_name: str = "Date",
                          years_past: int = 120) -> Tuple[bool, str]:
        """Validate that date is not too far in the past"""
        is_valid, message = InputValidator.validate_date(date_str, field_name)
        if not is_valid:
            return False, message
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = date.today()
            min_past_date = date(today.year - years_past, 1, 1)
            
            if date_obj < min_past_date:
                return False, f"{field_name} cannot be more than {years_past} years in the past"
            
            return True, ""
        except:
            return False, f"Invalid {field_name}"
    
    @staticmethod
    def validate_amount(amount_str: str, field_name: str = "Amount",
                       min_value: float = 0.0, 
                       max_value: float = 100000000.0) -> Tuple[bool, str]:
        """Validate monetary amount"""
        if not amount_str or not amount_str.strip():
            return False, f"{field_name} is required"
        
        amount_str = amount_str.strip()
        
        # Check format (digits with optional decimal point)
        if not re.match(r'^\d+(\.\d{1,2})?$', amount_str):
            return False, f"{field_name} must be a valid number (e.g., 1000.50)"
        
        try:
            amount = float(amount_str)
            
            # Check minimum value
            if amount < min_value:
                return False, f"{field_name} cannot be less than {min_value:,.2f}"
            
            # Check maximum value
            if amount > max_value:
                return False, f"{field_name} cannot exceed {max_value:,.2f}"
            
            # Check decimal places
            if '.' in amount_str:
                decimal_places = len(amount_str.split('.')[1])
                if decimal_places > 2:
                    return False, f"{field_name} can have maximum 2 decimal places"
            
            return True, ""
            
        except ValueError:
            return False, f"{field_name} must be a valid number"
    
    @staticmethod
    def validate_integer(value_str: str, field_name: str = "Value",
                        min_value: int = 0,
                        max_value: int = 1000000) -> Tuple[bool, str]:
        """Validate integer value"""
        if not value_str or not value_str.strip():
            return False, f"{field_name} is required"
        
        value_str = value_str.strip()
        
        # Check if it's a valid integer
        if not re.match(r'^\d+$', value_str):
            return False, f"{field_name} must be a whole number"
        
        try:
            value = int(value_str)
            
            if value < min_value:
                return False, f"{field_name} cannot be less than {min_value}"
            
            if value > max_value:
                return False, f"{field_name} cannot exceed {max_value}"
            
            return True, ""
            
        except ValueError:
            return False, f"{field_name} must be a valid number"
    
    @staticmethod
    def validate_student_code(code: str) -> Tuple[bool, str]:
        """Validate student code format"""
        if not code or not code.strip():
            return False, "Student code is required"
        
        code = code.strip().upper()
        
        # Check format: STU followed by digits
        if not re.match(r'^STU\d{4,}$', code):
            return False, "Student code must start with 'STU' followed by at least 4 digits"
        
        # Check length
        if len(code) > 20:
            return False, "Student code cannot exceed 20 characters"
        
        return True, ""
    
    @staticmethod
    def validate_teacher_code(code: str) -> Tuple[bool, str]:
        """Validate teacher code format"""
        if not code or not code.strip():
            return False, "Teacher code is required"
        
        code = code.strip().upper()
        
        # Check format: TCH followed by digits
        if not re.match(r'^TCH\d{3,}$', code):
            return False, "Teacher code must start with 'TCH' followed by at least 3 digits"
        
        # Check length
        if len(code) > 20:
            return False, "Teacher code cannot exceed 20 characters"
        
        return True, ""
    
    @staticmethod
    def validate_class_name(class_name: str) -> Tuple[bool, str]:
        """Validate class name format"""
        if not class_name or not class_name.strip():
            return False, "Class name is required"
        
        class_name = class_name.strip()
        
        # Check length
        if len(class_name) < 2:
            return False, "Class name must be at least 2 characters"
        
        if len(class_name) > 20:
            return False, "Class name cannot exceed 20 characters"
        
        # Check format: Grade XA or similar
        # Allow alphanumeric and spaces
        if not re.match(r'^[A-Za-z0-9\s\-]+$', class_name):
            return False, "Class name can only contain letters, numbers, spaces, and hyphens"
        
        return True, ""
    
    @staticmethod
    def validate_address(address: str) -> Tuple[bool, str]:
        """Validate address"""
        if not address or not address.strip():
            return True, ""  # Address is optional
        
        address = address.strip()
        
        # Check minimum length
        if len(address) < 5:
            return False, "Address must be at least 5 characters"
        
        # Check maximum length
        if len(address) > 200:
            return False, "Address cannot exceed 200 characters"
        
        # Check for valid characters (allow letters, numbers, spaces, commas, periods, hyphens)
        if not re.match(r'^[A-Za-z0-9\s\-\,\.\#]+$', address):
            return False, "Address can only contain letters, numbers, spaces, commas, periods, and hyphens"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str, confirm_password: str = None) -> Tuple[bool, str]:
        """Validate password"""
        if not password or not password.strip():
            return False, "Password is required"
        
        password = password.strip()
        
        # Check minimum length
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        # Check maximum length
        if len(password) > 50:
            return False, "Password cannot exceed 50 characters"
        
        # Check complexity
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>/?]', password):
            return False, "Password must contain at least one special character"
        
        # Check for common patterns
        common_patterns = ['password', '123456', 'qwerty', 'admin']
        if password.lower() in common_patterns:
            return False, "Password is too common. Choose a stronger password"
        
        # Check for sequential characters
        if re.search(r'(.)\1{2,}', password):
            return False, "Password cannot contain 3 or more identical characters in a row"
        
        # Check for sequential numbers or letters
        sequences = ['123', '234', '345', '456', '567', '678', '789', '890',
                    'abc', 'bcd', 'cde', 'def', 'efg', 'fgh', 'ghi', 'hij',
                    'ijk', 'jkl', 'klm', 'lmn', 'mno', 'nop', 'opq', 'pqr',
                    'qrs', 'rst', 'stu', 'tuv', 'uvw', 'vwx', 'wxy', 'xyz']
        
        password_lower = password.lower()
        for seq in sequences:
            if seq in password_lower:
                return False, "Password cannot contain sequential characters"
        
        # Confirm password if provided
        if confirm_password is not None and password != confirm_password:
            return False, "Passwords do not match"
        
        return True, ""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """Validate username"""
        if not username or not username.strip():
            return False, "Username is required"
        
        username = username.strip()
        
        # Check length
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if len(username) > 30:
            return False, "Username cannot exceed 30 characters"
        
        # Check format (letters, numbers, underscores, periods)
        if not re.match(r'^[A-Za-z0-9_.]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and periods"
        
        # Check if starts with letter
        if not re.match(r'^[A-Za-z]', username):
            return False, "Username must start with a letter"
        
        # Check for reserved usernames
        reserved = ['admin', 'administrator', 'root', 'system', 'user', 
                   'student', 'teacher', 'parent', 'school']
        if username.lower() in reserved:
            return False, "Username is reserved. Please choose a different username"
        
        return True, ""
    
    @staticmethod
    def validate_receipt_number(receipt: str) -> Tuple[bool, str]:
        """Validate receipt number format"""
        if not receipt or not receipt.strip():
            return True, ""  # Receipt number is optional
        
        receipt = receipt.strip().upper()
        
        # Check format: REC-YYYYMMDD-XXXX or EXP-YYYYMMDD-XXXX
        if not re.match(r'^(REC|EXP)-\d{8}-\d{4}$', receipt):
            return False, "Receipt number must be in format: REC-YYYYMMDD-XXXX or EXP-YYYYMMDD-XXXX"
        
        # Extract date from receipt
        date_str = receipt[4:12]
        try:
            datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            return False, "Invalid date in receipt number"
        
        return True, ""
    
    @staticmethod
    def validate_item_code(code: str) -> Tuple[bool, str]:
        """Validate inventory item code"""
        if not code or not code.strip():
            return False, "Item code is required"
        
        code = code.strip().upper()
        
        # Check format: XX followed by digits (e.g., BK001, PE100)
        if not re.match(r'^[A-Z]{2,3}\d{3,}$', code):
            return False, "Item code must start with 2-3 letters followed by at least 3 digits"
        
        # Check length
        if len(code) > 20:
            return False, "Item code cannot exceed 20 characters"
        
        return True, ""
    
    @staticmethod
    def validate_description(description: str, field_name: str = "Description") -> Tuple[bool, str]:
        """Validate description text"""
        if not description or not description.strip():
            return True, ""  # Description is optional
        
        description = description.strip()
        
        # Check minimum length
        if len(description) < 2:
            return False, f"{field_name} must be at least 2 characters"
        
        # Check maximum length
        if len(description) > 500:
            return False, f"{field_name} cannot exceed 500 characters"
        
        # Check for excessive whitespace
        if re.search(r'\s{4,}', description):
            return False, f"{field_name} cannot have excessive whitespace"
        
        return True, ""
    
    @staticmethod
    def validate_dropdown_selection(selection: str, field_name: str = "Selection") -> Tuple[bool, str]:
        """Validate dropdown selection"""
        if not selection or not selection.strip():
            return False, f"Please select a {field_name.lower()}"
        
        selection = selection.strip()
        
        # Check if selection contains the separator (:) used in combobox values
        if ':' in selection:
            # This is a combobox value with ID: Description format
            parts = selection.split(':')
            if len(parts) < 2 or not parts[0].strip().isdigit():
                return False, f"Invalid {field_name.lower()} selection"
        
        return True, ""


class FormValidator:
    """Form-level validation for complete forms"""
    
    @staticmethod
    def validate_student_form(form_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate complete student form"""
        errors = []
        
        # Required fields
        required_fields = [
            ('first_name', 'First Name'),
            ('last_name', 'Last Name'),
            ('class_name', 'Class'),
            ('enrollment_date', 'Enrollment Date')
        ]
        
        for field, label in required_fields:
            if field not in form_data or not form_data[field] or not str(form_data[field]).strip():
                errors.append(f"{label} is required")
        
        # Validate individual fields if no basic errors
        if not errors:
            # Validate names
            if 'first_name' in form_data and form_data['first_name']:
                is_valid, message = InputValidator.validate_name(
                    form_data['first_name'], "First Name"
                )
                if not is_valid:
                    errors.append(message)
            
            if 'last_name' in form_data and form_data['last_name']:
                is_valid, message = InputValidator.validate_name(
                    form_data['last_name'], "Last Name"
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate student code
            if 'student_code' in form_data and form_data['student_code']:
                is_valid, message = InputValidator.validate_student_code(
                    form_data['student_code']
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate class name
            if 'class_name' in form_data and form_data['class_name']:
                is_valid, message = InputValidator.validate_class_name(
                    form_data['class_name']
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate dates
            if 'birth_date' in form_data and form_data['birth_date']:
                today = date.today()
                min_birth_date = date(today.year - config.Config.VALIDATION['max_student_age'], 1, 1)
                max_birth_date = date(today.year - config.Config.VALIDATION['min_student_age'], 12, 31)
                
                is_valid, message = InputValidator.validate_date(
                    form_data['birth_date'], "Birth Date", 
                    min_date=min_birth_date, max_date=max_birth_date
                )
                if not is_valid:
                    errors.append(message)
            
            if 'enrollment_date' in form_data and form_data['enrollment_date']:
                is_valid, message = InputValidator.validate_date(
                    form_data['enrollment_date'], "Enrollment Date",
                    max_date=date.today()
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate phone
            if 'parent_phone' in form_data and form_data['parent_phone']:
                is_valid, message = InputValidator.validate_phone(
                    form_data['parent_phone']
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate email
            if 'parent_email' in form_data and form_data['parent_email']:
                is_valid, message = InputValidator.validate_email(
                    form_data['parent_email']
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate address
            if 'address' in form_data and form_data['address']:
                is_valid, message = InputValidator.validate_address(
                    form_data['address']
                )
                if not is_valid:
                    errors.append(message)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_teacher_form(form_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate complete teacher form"""
        errors = []
        
        # Required fields
        required_fields = [
            ('first_name', 'First Name'),
            ('last_name', 'Last Name'),
            ('hire_date', 'Hire Date')
        ]
        
        for field, label in required_fields:
            if field not in form_data or not form_data[field] or not str(form_data[field]).strip():
                errors.append(f"{label} is required")
        
        # Validate individual fields if no basic errors
        if not errors:
            # Validate names
            if 'first_name' in form_data and form_data['first_name']:
                is_valid, message = InputValidator.validate_name(
                    form_data['first_name'], "First Name"
                )
                if not is_valid:
                    errors.append(message)
            
            if 'last_name' in form_data and form_data['last_name']:
                is_valid, message = InputValidator.validate_name(
                    form_data['last_name'], "Last Name"
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate teacher code
            if 'teacher_code' in form_data and form_data['teacher_code']:
                is_valid, message = InputValidator.validate_teacher_code(
                    form_data['teacher_code']
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate dates
            if 'hire_date' in form_data and form_data['hire_date']:
                is_valid, message = InputValidator.validate_date(
                    form_data['hire_date'], "Hire Date",
                    max_date=date.today()
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate phone
            if 'phone' in form_data and form_data['phone']:
                is_valid, message = InputValidator.validate_phone(
                    form_data['phone']
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate email
            if 'email' in form_data and form_data['email']:
                is_valid, message = InputValidator.validate_email(
                    form_data['email']
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate specialization
            if 'subject_specialization' in form_data and form_data['subject_specialization']:
                specialization = str(form_data['subject_specialization']).strip()
                if len(specialization) > 100:
                    errors.append("Subject specialization cannot exceed 100 characters")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_fee_payment_form(form_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate fee payment form"""
        errors = []
        
        # Required fields
        required_fields = [
            ('student_id', 'Student'),
            ('fee_type_id', 'Fee Type'),
            ('amount', 'Amount'),
            ('payment_date', 'Payment Date')
        ]
        
        for field, label in required_fields:
            if field not in form_data or not form_data[field] or not str(form_data[field]).strip():
                errors.append(f"{label} is required")
        
        # Validate individual fields if no basic errors
        if not errors:
            # Validate amount
            if 'amount' in form_data and form_data['amount']:
                is_valid, message = InputValidator.validate_amount(
                    str(form_data['amount']), "Amount"
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate date
            if 'payment_date' in form_data and form_data['payment_date']:
                is_valid, message = InputValidator.validate_date(
                    form_data['payment_date'], "Payment Date",
                    max_date=date.today()
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate receipt number
            if 'receipt_number' in form_data and form_data['receipt_number']:
                is_valid, message = InputValidator.validate_receipt_number(
                    form_data['receipt_number']
                )
                if not is_valid:
                    errors.append(message)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_expense_form(form_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate expense form"""
        errors = []
        
        # Required fields
        required_fields = [
            ('description', 'Description'),
            ('amount', 'Amount'),
            ('expense_date', 'Expense Date'),
            ('category', 'Category')
        ]
        
        for field, label in required_fields:
            if field not in form_data or not form_data[field] or not str(form_data[field]).strip():
                errors.append(f"{label} is required")
        
        # Validate individual fields if no basic errors
        if not errors:
            # Validate amount
            if 'amount' in form_data and form_data['amount']:
                is_valid, message = InputValidator.validate_amount(
                    str(form_data['amount']), "Amount"
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate date
            if 'expense_date' in form_data and form_data['expense_date']:
                is_valid, message = InputValidator.validate_date(
                    form_data['expense_date'], "Expense Date",
                    max_date=date.today()
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate description
            if 'description' in form_data and form_data['description']:
                is_valid, message = InputValidator.validate_description(
                    form_data['description'], "Description"
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate receipt number
            if 'receipt_number' in form_data and form_data['receipt_number']:
                is_valid, message = InputValidator.validate_receipt_number(
                    form_data['receipt_number']
                )
                if not is_valid:
                    errors.append(message)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_inventory_form(form_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate inventory item form"""
        errors = []
        
        # Required fields
        required_fields = [
            ('item_name', 'Item Name'),
            ('category', 'Category'),
            ('quantity', 'Quantity'),
            ('unit_price', 'Unit Price')
        ]
        
        for field, label in required_fields:
            if field not in form_data or not form_data[field] or not str(form_data[field]).strip():
                errors.append(f"{label} is required")
        
        # Validate individual fields if no basic errors
        if not errors:
            # Validate item code
            if 'item_code' in form_data and form_data['item_code']:
                is_valid, message = InputValidator.validate_item_code(
                    form_data['item_code']
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate item name
            if 'item_name' in form_data and form_data['item_name']:
                item_name = str(form_data['item_name']).strip()
                if len(item_name) < 2:
                    errors.append("Item name must be at least 2 characters")
                if len(item_name) > 100:
                    errors.append("Item name cannot exceed 100 characters")
            
            # Validate quantity
            if 'quantity' in form_data and form_data['quantity']:
                is_valid, message = InputValidator.validate_integer(
                    str(form_data['quantity']), "Quantity",
                    min_value=0, max_value=100000
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate unit price
            if 'unit_price' in form_data and form_data['unit_price']:
                is_valid, message = InputValidator.validate_amount(
                    str(form_data['unit_price']), "Unit Price",
                    min_value=0, max_value=1000000
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate minimum quantity
            if 'min_quantity' in form_data and form_data['min_quantity']:
                is_valid, message = InputValidator.validate_integer(
                    str(form_data['min_quantity']), "Minimum Quantity",
                    min_value=0, max_value=10000
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate maximum quantity
            if 'max_quantity' in form_data and form_data['max_quantity']:
                is_valid, message = InputValidator.validate_integer(
                    str(form_data['max_quantity']), "Maximum Quantity",
                    min_value=1, max_value=100000
                )
                if not is_valid:
                    errors.append(message)
            
            # Check min <= max
            if ('min_quantity' in form_data and form_data['min_quantity'] and
                'max_quantity' in form_data and form_data['max_quantity']):
                try:
                    min_qty = int(form_data['min_quantity'])
                    max_qty = int(form_data['max_quantity'])
                    if min_qty > max_qty:
                        errors.append("Minimum quantity cannot exceed maximum quantity")
                except:
                    pass
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_attendance_form(form_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate attendance form"""
        errors = []
        
        # Required fields
        required_fields = [
            ('student_id', 'Student'),
            ('attendance_date', 'Date'),
            ('status', 'Status')
        ]
        
        for field, label in required_fields:
            if field not in form_data or not form_data[field] or not str(form_data[field]).strip():
                errors.append(f"{label} is required")
        
        # Validate individual fields if no basic errors
        if not errors:
            # Validate date
            if 'attendance_date' in form_data and form_data['attendance_date']:
                is_valid, message = InputValidator.validate_date(
                    form_data['attendance_date'], "Attendance Date",
                    max_date=date.today()
                )
                if not is_valid:
                    errors.append(message)
            
            # Validate status
            if 'status' in form_data and form_data['status']:
                valid_statuses = ['Present', 'Absent', 'Late', 'Excused']
                if form_data['status'] not in valid_statuses:
                    errors.append(f"Status must be one of: {', '.join(valid_statuses)}")
            
            # Validate times if provided
            if 'check_in_time' in form_data and form_data['check_in_time']:
                time_str = str(form_data['check_in_time']).strip()
                if time_str and not re.match(r'^\d{2}:\d{2}(:\d{2})?$', time_str):
                    errors.append("Check-in time must be in format HH:MM or HH:MM:SS")
            
            if 'check_out_time' in form_data and form_data['check_out_time']:
                time_str = str(form_data['check_out_time']).strip()
                if time_str and not re.match(r'^\d{2}:\d{2}(:\d{2})?$', time_str):
                    errors.append("Check-out time must be in format HH:MM or HH:MM:SS")
        
        return len(errors) == 0, errors


class ValidationWidgets:
    """Widgets with built-in validation"""
    
    @staticmethod
    def create_validated_entry(parent, label_text, validator_func=None, 
                             is_required=False, **kwargs):
        """Create entry widget with validation"""
        frame = tk.Frame(parent)
        
        # Label
        label = tk.Label(frame, text=label_text)
        label.pack(side='left', padx=(0, 10))
        
        # Entry
        entry_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=entry_var, **kwargs)
        entry.pack(side='left', fill='x', expand=True)
        
        # Validation label (hidden by default)
        validation_label = tk.Label(frame, text="", fg="red", font=("Arial", 8))
        validation_label.pack(side='left', padx=(5, 0))
        
        def validate():
            """Validate entry content"""
            value = entry_var.get().strip()
            
            if not value and is_required:
                validation_label.config(text="Required", fg="red")
                return False, "Required"
            
            if validator_func and value:
                is_valid, message = validator_func(value)
                if not is_valid:
                    validation_label.config(text=message, fg="red")
                    return False, message
                else:
                    validation_label.config(text="✓", fg="green")
                    return True, ""
            else:
                validation_label.config(text="")
                return True, ""
        
        def on_focus_out(event):
            """Validate when focus leaves"""
            validate()
        
        def on_key_release(event):
            """Validate on key release (with delay)"""
            # Clear validation message on typing
            validation_label.config(text="")
        
        # Bind events
        entry.bind('<FocusOut>', on_focus_out)
        entry.bind('<KeyRelease>', on_key_release)
        
        # Store validation function as attribute
        entry.validate = validate
        entry.get_validated_value = lambda: (entry_var.get().strip(), validate()[0])
        
        return frame, entry_var, entry
    
    @staticmethod
    def create_validated_combobox(parent, label_text, values=None, 
                                validator_func=None, is_required=False, **kwargs):
        """Create combobox widget with validation"""
        frame = tk.Frame(parent)
        
        # Label
        label = tk.Label(frame, text=label_text)
        label.pack(side='left', padx=(0, 10))
        
        # Combobox
        from tkinter import ttk
        combo_var = tk.StringVar()
        combobox = ttk.Combobox(frame, textvariable=combo_var, 
                               values=values or [], **kwargs)
        combobox.pack(side='left', fill='x', expand=True)
        
        # Validation label
        validation_label = tk.Label(frame, text="", fg="red", font=("Arial", 8))
        validation_label.pack(side='left', padx=(5, 0))
        
        def validate():
            """Validate combobox selection"""
            value = combo_var.get().strip()
            
            if not value and is_required:
                validation_label.config(text="Required", fg="red")
                return False, "Required"
            
            if validator_func and value:
                is_valid, message = validator_func(value)
                if not is_valid:
                    validation_label.config(text=message, fg="red")
                    return False, message
                else:
                    validation_label.config(text="✓", fg="green")
                    return True, ""
            else:
                validation_label.config(text="")
                return True, ""
        
        def on_focus_out(event):
            """Validate when focus leaves"""
            validate()
        
        def on_selection_change(event):
            """Validate on selection change"""
            validate()
        
        # Bind events
        combobox.bind('<FocusOut>', on_focus_out)
        combobox.bind('<<ComboboxSelected>>', on_selection_change)
        
        # Store validation function
        combobox.validate = validate
        combobox.get_validated_value = lambda: (combo_var.get().strip(), validate()[0])
        
        return frame, combo_var, combobox
    
    @staticmethod
    def create_validated_spinbox(parent, label_text, from_, to, 
                               validator_func=None, is_required=False, **kwargs):
        """Create spinbox widget with validation"""
        frame = tk.Frame(parent)
        
        # Label
        label = tk.Label(frame, text=label_text)
        label.pack(side='left', padx=(0, 10))
        
        # Spinbox
        spin_var = tk.StringVar()
        spinbox = tk.Spinbox(frame, from_=from_, to=to, textvariable=spin_var, **kwargs)
        spinbox.pack(side='left', fill='x', expand=True)
        
        # Validation label
        validation_label = tk.Label(frame, text="", fg="red", font=("Arial", 8))
        validation_label.pack(side='left', padx=(5, 0))
        
        def validate():
            """Validate spinbox value"""
            value = spin_var.get().strip()
            
            if not value and is_required:
                validation_label.config(text="Required", fg="red")
                return False, "Required"
            
            if validator_func and value:
                is_valid, message = validator_func(value)
                if not is_valid:
                    validation_label.config(text=message, fg="red")
                    return False, message
                else:
                    validation_label.config(text="✓", fg="green")
                    return True, ""
            else:
                validation_label.config(text="")
                return True, ""
        
        def on_focus_out(event):
            """Validate when focus leaves"""
            validate()
        
        # Bind events
        spinbox.bind('<FocusOut>', on_focus_out)
        
        # Store validation function
        spinbox.validate = validate
        spinbox.get_validated_value = lambda: (spin_var.get().strip(), validate()[0])
        
        return frame, spin_var, spinbox
    
    @staticmethod
    def highlight_invalid_widget(widget, is_invalid=True):
        """Highlight widget with red border if invalid"""
        if is_invalid:
            widget.config(highlightbackground="red", highlightcolor="red", 
                         highlightthickness=2)
        else:
            widget.config(highlightbackground="gray", highlightcolor="gray", 
                         highlightthickness=1)


class ValidationHelper:
    """Helper functions for validation in UI"""
    
    @staticmethod
    def validate_all_widgets(widgets: List) -> Tuple[bool, List[str]]:
        """Validate all widgets in a list"""
        errors = []
        all_valid = True
        
        for widget in widgets:
            if hasattr(widget, 'validate'):
                is_valid, message = widget.validate()
                if not is_valid and message:
                    errors.append(message)
                    all_valid = False
                    ValidationHelper.highlight_widget_error(widget, True)
                else:
                    ValidationHelper.highlight_widget_error(widget, False)
        
        return all_valid, errors
    
    @staticmethod
    def highlight_widget_error(widget, has_error=True):
        """Highlight widget to show error state"""
        try:
            if has_error:
                widget.config(foreground="red", background="#FFE6E6")
                # Add red border if it's an Entry widget
                if isinstance(widget, tk.Entry):
                    widget.config(highlightbackground="red", 
                                 highlightcolor="red", 
                                 highlightthickness=2)
            else:
                widget.config(foreground="black", background="white")
                if isinstance(widget, tk.Entry):
                    widget.config(highlightbackground="gray", 
                                 highlightcolor="gray", 
                                 highlightthickness=1)
        except:
            pass
    
    @staticmethod
    def show_validation_errors(errors: List[str], title: str = "Validation Error"):
        """Show validation errors in a message box"""
        if errors:
            error_message = "Please correct the following errors:\n\n"
            for i, error in enumerate(errors, 1):
                error_message += f"{i}. {error}\n"
            
            messagebox.showerror(title, error_message)
            return False
        return True
    
    @staticmethod
    def format_phone_number(phone: str) -> str:
        """Format phone number for display"""
        if not phone:
            return ""
        
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) == 10 and digits.startswith('0'):
            # Local format: 0XXXXXXXXX -> 0XXX XXX XXX
            return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
        elif len(digits) == 12 and digits.startswith('265'):
            # International without +: 265XXXXXXXXX -> +255 XXX XXX XXX
            return f"+{digits[:3]} {digits[3:6]} {digits[6:9]} {digits[9:]}"
        elif len(digits) == 13 and digits.startswith('265'):
            # International with + already: +255XXXXXXXXX -> +255 XXX XXX XXX
            return f"+{digits[:3]} {digits[3:6]} {digits[6:9]} {digits[9:]}"
        
        return phone
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """Format amount as currency"""
        try:
            from utils.helpers import format_currency as _fmt
            return _fmt(float(amount))
        except:
            try:
                return f"{float(amount):,.2f}"
            except:
                return str(amount)
    
    @staticmethod
    def parse_currency(currency_str: str) -> float:
        """Parse currency string to float"""
        if not currency_str:
            return 0.0
        
        # Remove currency symbols and commas
        clean_str = re.sub(r'[^\d\.]', '', currency_str)
        
        try:
            return float(clean_str)
        except:
            return 0.0
    
    @staticmethod
    def format_date_for_display(date_str: str) -> str:
        """Format date string for display"""
        if not date_str:
            return ""
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            return date_obj.strftime('%d %b %Y')
        except:
            return date_str
    
    @staticmethod
    def format_date_for_input(date_obj: date) -> str:
        """Format date object for input field"""
        if not date_obj:
            return ""
        
        return date_obj.strftime('%Y-%m-%d')
    
    @staticmethod
    def get_today_date() -> str:
        """Get today's date in YYYY-MM-DD format"""
        return date.today().strftime('%Y-%m-%d')
    
    @staticmethod
    def validate_and_convert_date(date_str: str, field_name: str = "Date") -> Tuple[bool, Optional[date], str]:
        """Validate date string and convert to date object"""
        is_valid, message = InputValidator.validate_date(date_str, field_name)
        
        if not is_valid:
            return False, None, message
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            return True, date_obj, ""
        except:
            return False, None, f"Invalid {field_name}"
    
    @staticmethod
    def validate_and_convert_amount(amount_str: str, field_name: str = "Amount") -> Tuple[bool, Optional[float], str]:
        """Validate amount string and convert to float"""
        is_valid, message = InputValidator.validate_amount(amount_str, field_name)
        
        if not is_valid:
            return False, None, message
        
        try:
            amount = float(amount_str)
            return True, amount, ""
        except:
            return False, None, f"Invalid {field_name}"
    
    @staticmethod
    def validate_and_convert_integer(value_str: str, field_name: str = "Value") -> Tuple[bool, Optional[int], str]:
        """Validate integer string and convert to int"""
        is_valid, message = InputValidator.validate_integer(value_str, field_name)
        
        if not is_valid:
            return False, None, message
        
        try:
            value = int(value_str)
            return True, value, ""
        except:
            return False, None, f"Invalid {field_name}"


# Pre-configured validator functions for common fields
class ValidatorPresets:
    """Pre-configured validator functions"""
    
    @staticmethod
    def student_first_name():
        """Validator for student first name"""
        return lambda x: InputValidator.validate_name(x, "First Name")
    
    @staticmethod
    def student_last_name():
        """Validator for student last name"""
        return lambda x: InputValidator.validate_name(x, "Last Name")
    
    @staticmethod
    def student_code():
        """Validator for student code"""
        return InputValidator.validate_student_code
    
    @staticmethod
    def class_name():
        """Validator for class name"""
        return InputValidator.validate_class_name
    
    @staticmethod
    def phone():
        """Validator for phone number"""
        return InputValidator.validate_phone
    
    @staticmethod
    def email():
        """Validator for email"""
        return InputValidator.validate_email
    
    @staticmethod
    def birth_date():
        """Validator for birth date"""
        today = date.today()
        min_date = date(today.year - config.Config.VALIDATION['max_student_age'], 1, 1)
        max_date = date(today.year - config.Config.VALIDATION['min_student_age'], 12, 31)
        return lambda x: InputValidator.validate_date(x, "Birth Date", 
                                                     min_date=min_date, max_date=max_date)
    
    @staticmethod
    def enrollment_date():
        """Validator for enrollment date"""
        return lambda x: InputValidator.validate_date(x, "Enrollment Date", 
                                                     max_date=date.today())
    
    @staticmethod
    def amount(min_value=0.0, max_value=1000000.0):
        """Validator for amount"""
        return lambda x: InputValidator.validate_amount(x, "Amount", 
                                                       min_value=min_value, 
                                                       max_value=max_value)
    
    @staticmethod
    def date(field_name="Date", max_date=None):
        """Validator for date"""
        return lambda x: InputValidator.validate_date(x, field_name, 
                                                     max_date=max_date or date.today())
    
    @staticmethod
    def integer(field_name="Value", min_value=0, max_value=1000000):
        """Validator for integer"""
        return lambda x: InputValidator.validate_integer(x, field_name, 
                                                        min_value=min_value, 
                                                        max_value=max_value)
    
    @staticmethod
    def receipt_number():
        """Validator for receipt number"""
        return InputValidator.validate_receipt_number
    
    @staticmethod
    def item_code():
        """Validator for item code"""
        return InputValidator.validate_item_code
    
    @staticmethod
    def description(field_name="Description"):
        """Validator for description"""
        return lambda x: InputValidator.validate_description(x, field_name)


# Example usage in a form:
"""
# Create validated widgets
name_frame, name_var, name_entry = ValidationWidgets.create_validated_entry(
    parent, "Student Name:", 
    validator_func=ValidatorPresets.student_name(),
    is_required=True,
    width=30
)

phone_frame, phone_var, phone_entry = ValidationWidgets.create_validated_entry(
    parent, "Phone:", 
    validator_func=ValidatorPresets.phone(),
    is_required=False,
    width=20
)

# Validate all widgets before submission
widgets = [name_entry, phone_entry]
is_valid, errors = ValidationHelper.validate_all_widgets(widgets)

if is_valid:
    # Process form
    pass
else:
    ValidationHelper.show_validation_errors(errors)
"""