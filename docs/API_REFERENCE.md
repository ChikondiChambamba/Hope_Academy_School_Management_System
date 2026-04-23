# Hope Academy School Management System - API Reference

## Table of Contents
1. [Database API](#database-api)
2. [Student Model API](#student-model-api)
3. [Finance Model API](#finance-model-api)
4. [Attendance Model API](#attendance-model-api)
5. [Teacher Model API](#teacher-model-api)
6. [Inventory Model API](#inventory-model-api)
7. [Utility Functions](#utility-functions)
8. [UI Components](#ui-components)

---

## Database API

### `DatabaseConnection` Class

Singleton class managing MySQL database connections with connection pooling.

#### Methods

##### `get_connection() -> mysql.connector.MySQLConnection`
Returns a connection from the pool.

```python
from database.connection import DatabaseConnection

db = DatabaseConnection()
connection = db.get_connection()
try:
    cursor = connection.cursor(dictionary=True)
    # Use cursor
finally:
    cursor.close()
    connection.close()
```

**Returns**: MySQL connection object
**Raises**: `mysql.connector.Error` on connection failure
**Thread-safe**: Yes

---

##### `execute_query(query: str, params: Tuple = None, fetch: bool = False) -> Optional[List[Dict]]`
Executes a SQL query with automatic connection management.

```python
from database.connection import DatabaseConnection

db = DatabaseConnection()

# SELECT query
results = db.execute_query(
    "SELECT * FROM students WHERE class = %s",
    ("Grade 1",),
    fetch=True
)

# INSERT/UPDATE query
last_id = db.execute_query(
    "INSERT INTO students (first_name, last_name, class) VALUES (%s, %s, %s)",
    ("John", "Doe", "Grade 1")
)
```

**Parameters**:
- `query` (str): SQL query with %s placeholders
- `params` (Tuple): Query parameters for binding
- `fetch` (bool): If True, returns query results; if False, commits and returns last insert ID

**Returns**:
- If `fetch=True`: List of dictionaries (one per row)
- If `fetch=False`: Last inserted row ID

**Raises**: `mysql.connector.Error` on database error

**Features**:
- Automatic transaction management
- Automatic rollback on error
- Connection pool management
- Parameter binding (prevents SQL injection)

---

##### `execute_many(query: str, params_list: List[Tuple]) -> None`
Executes multiple INSERT/UPDATE statements in batch.

```python
db = DatabaseConnection()

params = [
    ("Student1", "Class1", "2025-01-15"),
    ("Student2", "Class1", "2025-01-15"),
    ("Student3", "Class2", "2025-01-15")
]

db.execute_many(
    "INSERT INTO students (student_code, class, enrollment_date) VALUES (%s, %s, %s)",
    params
)
```

**Parameters**:
- `query` (str): SQL query template
- `params_list` (List[Tuple]): List of parameter tuples

**Raises**: `mysql.connector.Error` on error

**Features**:
- Batch processing for performance
- Single transaction for all rows
- Automatic rollback on error

---

##### `test_connection() -> bool`
Tests database connectivity.

```python
from database.connection import DatabaseConnection

db = DatabaseConnection()
if db.test_connection():
    print("Database is accessible")
else:
    print("Database connection failed")
```

**Returns**: True if connection successful, False otherwise
**Usage**: Initial startup checks

---

## Student Model API

### `Student` Dataclass

Represents a student with validation and persistence logic.

#### Fields

```python
@dataclass
class Student:
    student_id: Optional[int] = None          # Database ID (auto-generated)
    student_code: str = ""                    # Unique code (e.g., "STU001")
    first_name: str = ""                      # Required
    last_name: str = ""                       # Required
    class_name: str = ""                      # Required
    birth_date: Optional[date] = None         # Validated: 3-18 years
    parent_name: str = ""                     # Contact person
    parent_phone: str = ""                    # Validated phone format
    parent_email: str = ""                    # Validated email format
    address: str = ""                         # Full address
    enrollment_date: Optional[date] = None    # Required
    is_active: bool = True                    # Soft delete flag
    is_new: bool = True                       # New vs returning student
    created_at: Optional[datetime] = None     # Auto-managed
    updated_at: Optional[datetime] = None     # Auto-managed
    
    # Computed fields (not in database)
    total_paid: float = 0.0                   # Calculated from payments
    total_due: float = 0.0                    # Calculated from fees
    balance: float = 0.0                      # Calculated: due - paid
```

#### Methods

##### `validate() -> tuple[bool, str]`
Validates student data before saving.

```python
student = Student(
    first_name="John",
    last_name="Doe",
    class_name="Grade 1",
    enrollment_date=date(2025, 1, 15),
    birth_date=date(2018, 6, 20)
)

is_valid, error_message = student.validate()
if not is_valid:
    print(f"Validation error: {error_message}")
```

**Validation Rules**:
- First name, last name, class_name required
- Enrollment date cannot be in future
- Birth date cannot be in future
- Student age must be 3-18 years
- Phone format must be valid (optional)
- Email format must be valid (optional)

**Returns**: Tuple of (bool, str) - validation result and error message

---

##### `save() -> tuple[bool, str]`
Saves or updates student in database.

```python
student = Student(
    first_name="Jane",
    last_name="Smith",
    class_name="Grade 2",
    enrollment_date=date(2025, 1, 15)
)

success, message = student.save()
if success:
    print(f"Student saved with ID: {student.student_id}")
else:
    print(f"Error: {message}")
```

**Logic**:
- Validates data first
- If `student_id` exists: updates existing record
- If `student_id` is None: creates new record
- Auto-generates student code if needed

**Returns**: Tuple of (bool, str) - success flag and message

**Side Effects**:
- Sets `student_id` on insert
- Updates `updated_at` timestamp
- Generates student code if not provided

---

##### `delete() -> bool`
Soft-deletes student (sets is_active=False).

```python
if student.delete():
    print("Student deactivated")
```

**Returns**: True on success, False on failure

**Note**: Marks as inactive rather than deleting (preserves history)

---

##### `to_dict() -> Dict[str, Any]`
Converts student to dictionary for serialization.

```python
student = Student.get_by_id(1)
data = student.to_dict()
print(data)  # {'student_id': 1, 'first_name': 'John', ...}
```

**Returns**: Dictionary representation of all fields

---

#### Class Methods

##### `get_all(academic_year: str) -> List[Student]`
Retrieves all active students.

```python
students = Student.get_all("2025-2026")
for student in students:
    print(f"{student.first_name} - Balance: {student.balance}")
```

**Returns**: List of Student objects with computed fields

---

##### `get_by_id(student_id: int, academic_year: str) -> Optional[Student]`
Retrieves specific student by ID.

```python
student = Student.get_by_id(123, "2025-2026")
if student:
    print(student.full_name)
else:
    print("Student not found")
```

**Returns**: Student object or None if not found

---

##### `search(search_term: str, academic_year: str) -> List[Student]`
Searches students by name or code.

```python
results = Student.search("John", "2025-2026")
# Searches: first_name, last_name, student_code
```

**Returns**: List of matching Student objects

---

##### `get_by_class(class_name: str, academic_year: str) -> List[Student]`
Retrieves all students in a specific class.

```python
grade_1_students = Student.get_by_class("Grade 1", "2025-2026")
print(f"Total students: {len(grade_1_students)}")
```

**Returns**: List of Student objects in class

---

---

## Finance Model API

### `FeeType` Dataclass

Represents a configurable fee type (e.g., tuition, uniform, registration).

#### Fields

```python
@dataclass
class FeeType:
    fee_type_id: Optional[int] = None
    fee_name: str = ""                # e.g., "Tuition", "Uniform"
    description: str = ""
    amount: float = 0.0               # Fee amount in currency
    term: str = ""                    # Term applicability
    academic_year: str = ""           # Required for filtering
    is_required: bool = True          # Is this fee mandatory?
    created_at: Optional[datetime] = None
```

#### Methods

##### `validate() -> tuple[bool, str]`
Validates fee type data.

```python
fee = FeeType(
    fee_name="Tuition",
    amount=50000.00,
    academic_year="2025-2026"
)

is_valid, error = fee.validate()
```

**Validation**:
- Fee name required and non-empty
- Amount > 0
- Academic year required

**Returns**: Tuple of (bool, str)

---

##### `save() -> tuple[bool, str]`
Saves or updates fee type.

```python
fee = FeeType(
    fee_name="Sports Fund",
    amount=10000.00,
    academic_year="2025-2026"
)

success, message = fee.save()
```

**Returns**: Tuple of (bool, str)

---

##### `delete() -> bool`
Deletes fee type.

```python
success = fee.delete()
```

**Returns**: True/False

**Note**: Preserves existing payments (uses soft delete or cascade carefully)

---

### `FeePayment` Dataclass

Represents a student fee payment.

#### Fields

```python
@dataclass
class FeePayment:
    fee_id: Optional[int] = None
    student_id: int = 0                    # Required
    fee_type_id: int = 0                   # Required
    amount_paid: float = 0.0               # Required, > 0
    payment_date: Optional[date] = None    # Defaults to today
    payment_method: str = "Cash"           # Cash/Mobile money/Bank/Check
    receipt_number: str = ""               # Auto-generated if empty
    description: str = ""                  # Optional notes
    academic_year: str = ""
    created_at: Optional[datetime] = None
```

#### Methods

##### `validate() -> tuple[bool, str]`
Validates payment data.

```python
payment = FeePayment(
    student_id=1,
    fee_type_id=2,
    amount_paid=25000.00,
    payment_date=date.today()
)

is_valid, error = payment.validate()
```

**Validation**:
- Student and fee type exist
- Amount > 0
- Payment date not in future
- Payment method recognized

**Returns**: Tuple of (bool, str)

---

##### `save() -> tuple[bool, str]`
Records payment in database.

```python
payment = FeePayment(
    student_id=1,
    fee_type_id=2,
    amount_paid=25000.00
)

success, message = payment.save()
if success:
    print(f"Payment recorded. Receipt: {payment.receipt_number}")
```

**Features**:
- Auto-generates receipt number if empty
- Atomic receipt generation
- Auto-applies fee exemptions if needed
- Updates student balance

**Returns**: Tuple of (bool, str)

**Side Effects**:
- Inserts into `student_fees` table
- May insert into `student_fee_exemptions` table
- Sets `receipt_number`

---

##### `generate_receipt_number() -> str`
Generates unique receipt number.

```python
receipt = payment.generate_receipt_number()
# Format: REC-YYYYMMDD-0001
```

**Format**: `REC-YYYYMMDD-XXXX` (per-day counter)

**Returns**: Unique receipt string

**Note**: Uses atomic database counter for thread-safety

---

### `FeeExemption` Dataclass

Represents a fee exemption for a student.

#### Fields

```python
@dataclass
class FeeExemption:
    exemption_id: Optional[int] = None
    student_id: int = 0
    fee_type_id: int = 0
    reason: str = ""                  # Why exemption granted
    created_at: Optional[datetime] = None
```

#### Methods

##### `save() -> tuple[bool, str]`
Saves exemption record.

```python
exemption = FeeExemption(
    student_id=5,
    fee_type_id=3,
    reason="Scholarship recipient"
)

success, message = exemption.save()
```

**Returns**: Tuple of (bool, str)

---

### `Expense` Dataclass

Represents an operational expense.

#### Fields

```python
@dataclass
class Expense:
    expense_id: Optional[int] = None
    expense_date: Optional[date] = None     # Required
    item_id: int = 0                        # Inventory item
    description: str = ""                   # Required
    amount: float = 0.0                     # Required, > 0
    category: str = ""                      # Expense category
    payment_method: str = "Cash"
    receipt_number: str = ""                # Auto-generated
    notes: str = ""
    created_at: Optional[datetime] = None
```

#### Methods

##### `validate() -> tuple[bool, str]`
Validates expense data.

```python
expense = Expense(
    expense_date=date.today(),
    description="Stationery supplies",
    amount=15000.00,
    category="Supplies"
)

is_valid, error = expense.validate()
```

**Returns**: Tuple of (bool, str)

---

##### `save() -> tuple[bool, str]`
Saves expense record.

```python
success, message = expense.save()
if success:
    print(f"Expense recorded. Receipt: {expense.receipt_number}")
```

**Features**:
- Auto-generates receipt number
- Records date and time
- Links to inventory if applicable

**Returns**: Tuple of (bool, str)

---

---

## Attendance Model API

### `Attendance` Dataclass

Represents daily student attendance record.

#### Fields

```python
@dataclass
class Attendance:
    attendance_id: Optional[int] = None
    student_id: int = 0                     # Required
    class_name: str = ""                    # Required
    attendance_date: Optional[date] = None  # Required
    is_present: bool = True                 # Present/Absent
    recorded_by: str = ""                   # Username
    notes: str = ""                         # Optional notes
    created_at: Optional[datetime] = None
```

#### Methods

##### `save() -> tuple[bool, str]`
Records attendance.

```python
attendance = Attendance(
    student_id=1,
    class_name="Grade 1",
    attendance_date=date.today(),
    is_present=True,
    recorded_by="teacher1"
)

success, message = attendance.save()
```

**Returns**: Tuple of (bool, str)

---

##### `get_class_statistics(class_name: str, start_date: date, end_date: date) -> Dict`
Retrieves class attendance statistics.

```python
stats = Attendance.get_class_statistics(
    "Grade 1",
    date(2025, 1, 1),
    date(2025, 1, 31)
)
# Returns: {'total_days': 20, 'present': 19, 'absent': 1, 'rate': 95.0}
```

**Returns**: Dictionary with statistics

---

---

## Teacher Model API

### `Teacher` Dataclass

Represents a teacher record.

#### Fields

```python
@dataclass
class Teacher:
    teacher_id: Optional[int] = None
    teacher_code: str = ""                  # Unique code
    first_name: str = ""                    # Required
    last_name: str = ""                     # Required
    phone: str = ""                         # Validated phone
    email: str = ""                         # Validated email
    subject_specialization: str = ""        # Subject taught
    hire_date: Optional[date] = None        # Required
    salary_amount: float = 0.0              # Monthly salary
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

#### Methods

##### `save() -> tuple[bool, str]`
Saves or updates teacher.

```python
teacher = Teacher(
    first_name="James",
    last_name="Smith",
    subject_specialization="Mathematics",
    hire_date=date(2020, 1, 15),
    salary_amount=500000.00
)

success, message = teacher.save()
```

**Returns**: Tuple of (bool, str)

---

##### `get_salary_history(start_date: date, end_date: date) -> List[Dict]`
Retrieves salary payment history.

```python
history = teacher.get_salary_history(
    date(2025, 1, 1),
    date(2025, 12, 31)
)
```

**Returns**: List of salary transactions

---

---

## Inventory Model API

### `InventoryItem` Dataclass

Represents an inventory item.

#### Fields

```python
@dataclass
class InventoryItem:
    item_id: Optional[int] = None
    item_name: str = ""                     # Required
    category: str = ""                      # Item category
    quantity_in_stock: int = 0              # Current stock
    reorder_level: int = 0                  # Alert threshold
    unit_price: float = 0.0                 # Cost per unit
    last_restocked: Optional[date] = None
    supplier: str = ""                      # Supplier name
    created_at: Optional[datetime] = None
```

#### Methods

##### `save() -> tuple[bool, str]`
Saves inventory item.

```python
item = InventoryItem(
    item_name="Exercise Books",
    category="Stationery",
    quantity_in_stock=500,
    reorder_level=100,
    unit_price=500.00
)

success, message = item.save()
```

**Returns**: Tuple of (bool, str)

---

##### `get_low_stock_items() -> List[InventoryItem]`
Retrieves items below reorder level.

```python
low_stock = InventoryItem.get_low_stock_items()
for item in low_stock:
    print(f"{item.item_name}: {item.quantity_in_stock} (reorder at {item.reorder_level})")
```

**Returns**: List of low-stock items

---

---

## Utility Functions

### `helpers.py`

#### `format_currency(amount: float) -> str`
Formats amount as currency string.

```python
from utils.helpers import format_currency

print(format_currency(50000.00))  # Output: "MK 50,000.00"
```

**Returns**: Formatted currency string

---

#### `parse_currency(value: str) -> float`
Parses currency string to float.

```python
from utils.helpers import parse_currency

amount = parse_currency("MK 50,000.00")  # Returns: 50000.0
```

**Returns**: Float amount

**Features**: Handles various currency formats

---

#### `format_date(date_obj) -> str`
Formats date as string.

```python
from utils.helpers import format_date

date_str = format_date(date(2025, 1, 15))  # "2025-01-15"
```

**Returns**: Formatted date string (YYYY-MM-DD)

---

#### `parse_date(date_str: str) -> Optional[date]`
Parses date string.

```python
from utils.helpers import parse_date

d = parse_date("2025-01-15")  # Returns: date object
```

**Returns**: date object or None if invalid

---

#### `calculate_age(birth_date: date) -> int`
Calculates age from birth date.

```python
from utils.helpers import calculate_age

age = calculate_age(date(2015, 6, 20))  # Calculates current age
```

**Returns**: Age in years

---

#### `generate_student_code(class_name: str) -> str`
Generates unique student code.

```python
from utils.helpers import generate_student_code

code = generate_student_code("Grade 1")  # "STU-G1-00001"
```

**Returns**: Unique student code

**Format**: `STU-{CLASS_ABBREV}-{COUNTER}`

---

### `validators.py`

#### `Validators.validate_email(email: str) -> bool`
Validates email format.

```python
from utils.validators import Validators

if Validators.validate_email("user@example.com"):
    print("Valid email")
```

**Returns**: True if valid, False otherwise

**Pattern**: RFC 5322 simplified pattern

---

#### `Validators.validate_phone(phone: str) -> bool`
Validates phone number format.

```python
from utils.validators import Validators

if Validators.validate_phone("+265123456789"):
    print("Valid phone")
```

**Returns**: True if valid, False otherwise

**Supports**: Malawian +265, various formats

---

### `export_import.py`

#### `backup_database(output_path: str = None) -> bool`
Creates database backup.

```python
from utils.export_import import backup_database

if backup_database():
    print("Backup created successfully")
```

**Returns**: True on success, False on failure

**Methods**:
1. Primary: Uses `mysqldump` command-line tool
2. Fallback: Manual CSV export per table

**Output**: Compressed SQL or CSV files

---

#### `restore_database(backup_file: str) -> bool`
Restores database from backup.

```python
from utils.export_import import restore_database

if restore_database("backup_20250115_120000.sql"):
    print("Database restored")
```

**Returns**: True on success, False on failure

**Requires**: `mysql` command-line tool available

---

#### `export_all_data(output_dir: str = None) -> bool`
Exports all tables to CSV files.

```python
from utils.export_import import export_all_data

if export_all_data():
    print("Data exported to CSV")
```

**Returns**: True on success, False on failure

**Output**: CSV files per table in exports directory

---

---

## UI Components

### Main Window

#### `MainWindow` Class

Main application window with tab management.

##### Methods

##### `create_tabs()`
Dynamically creates tabs based on user role.

```python
# Called automatically, creates Dashboard, Students, Finance, etc.
# based on Config.has_permission(feature)
```

---

##### `refresh_all()`
Refreshes all visible tabs.

```python
# Triggered by <<PaymentRecorded>> event
# Causes all tabs to reload data
```

---

### Tab Classes

#### `DashboardTab`
Quick statistics and shortcuts.

**Events Monitored**:
- `<<PaymentRecorded>>`: Refresh statistics
- `<<StudentAdded>>`: Update counts

---

#### `StudentsTab`
Student management interface.

**Methods**:
- `add_student()`: Opens add dialog
- `edit_student()`: Opens edit dialog
- `search_students()`: Searches by criteria
- `refresh_list()`: Reloads student list

---

#### `FinanceTab`
Payment and expense recording.

**Methods**:
- `record_payment()`: Records fee payment
- `record_expense()`: Records operational expense
- `view_balances()`: Shows student fee balances
- `generate_report()`: Creates financial report

---

### Dialog Classes

#### `StudentDialog`
Modal for adding/editing students.

```python
from UI.dialogs import StudentDialog

dialog = StudentDialog(parent_window, student=existing_student)
if dialog.show():
    # Student was saved
    student = dialog.get_result()
```

---

#### `PaymentDialog`
Modal for recording payments.

```python
from UI.dialogs import PaymentDialog

dialog = PaymentDialog(parent_window)
if dialog.show():
    # Payment was recorded
```

---

---

## Event System

### Custom Events

**`<<PaymentRecorded>>`**
- Emitted when: Fee payment is saved
- Handled by: All tabs (refresh balance displays)
- Usage: `self.root.event_generate("<<PaymentRecorded>>")`

**`<<UserRoleChanged>>`**
- Emitted when: User logs in / role changes
- Handled by: Main window (recreates tabs)
- Usage: `self.root.event_generate("<<UserRoleChanged>>")`

**`<<PreferencesChanged>>`**
- Emitted when: Settings updated
- Handled by: Main window (applies theme, DB connection)
- Usage: `self.root.event_generate("<<PreferencesChanged>>")`

---

## Error Handling

### Exception Hierarchy

```python
try:
    # Database operation
    db.execute_query(...)
except mysql.connector.Error as e:
    # Database-specific error
    logger.error(f"Database error: {e}")
except Exception as e:
    # Catch-all
    logger.error(f"Unexpected error: {e}")
finally:
    # Cleanup
    connection.close()
```

### User-Facing Messages

All operations return tuples of (success: bool, message: str):

```python
success, message = student.save()
if success:
    messagebox.showinfo("Success", message)
else:
    messagebox.showerror("Error", message)
```

---

## Configuration API

### `Config` Class

#### Static Methods

##### `has_permission(feature: str) -> bool`
Checks if current user role has permission for feature.

```python
from config import Config

if Config.has_permission('finance'):
    # Show finance tab
```

**Returns**: True/False

---

##### `set_current_user(username: str) -> bool`
Sets the logged-in user.

```python
if Config.set_current_user("admin"):
    print("User set successfully")
```

**Returns**: True on success, False if user not found

---

##### `verify_user_credentials(username: str, password: str) -> bool`
Verifies user password.

```python
if Config.verify_user_credentials("admin", "password123"):
    print("Credentials valid")
```

**Returns**: True if credentials match

---

---

## Logging

### Setup

```python
from utils.helpers import setup_logging

logger = setup_logging()
logger.info("Application started")
logger.error("An error occurred", exc_info=True)
```

**Log Location**: `data/logs/app.log`

**Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

**Document Version**: 1.0  
**Last Updated**: January 2026

