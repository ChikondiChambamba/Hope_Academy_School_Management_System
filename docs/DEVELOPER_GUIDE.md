# Hope Academy School Management System - Developer Guide

## Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure Overview](#project-structure-overview)
3. [Code Style & Conventions](#code-style--conventions)
4. [Adding New Features](#adding-new-features)
5. [Testing Guidelines](#testing-guidelines)
6. [Debugging Tips](#debugging-tips)
7. [Database Migration](#database-migration)
8. [Version Control Workflow](#version-control-workflow)
9. [Performance Optimization](#performance-optimization)
10. [Common Pitfalls](#common-pitfalls)

---

## Development Environment Setup

### Prerequisites
- Python 3.8 or higher
- MySQL 5.7 or higher
- Git for version control
- Virtual environment support

### Step 1: Clone Repository
```bash
git clone https://github.com/ChikondiChambamba/Hope_Academy_School_Management_System.git
cd Hope_Academy_School_Management_System
```

### Step 2: Create Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Database
Edit `config.py`:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',
    'database': 'school_management',
    'port': 3306,
}
```

### Step 5: Initialize Database
```bash
# Create database and tables
python setup_database.py

# Verify
python scripts/check_classes.py
```

### Step 6: Run Application
```bash
python main.py
```

---

## Project Structure Overview

### Key Directories

#### `database/`
- **Purpose**: Data access layer
- **Files**:
  - `connection.py`: Connection pooling singleton
  - `queries.py`: Centralized SQL queries
  - `schema.sql`: Database schema definition
- **When to modify**: New queries, connection improvements

#### `models/`
- **Purpose**: Business logic and data models
- **Files**:
  - `student.py`: Student CRUD and validation
  - `finance.py`: Financial models
  - `attendance.py`: Attendance tracking
  - `teacher.py`: Teacher management
  - `inventory.py`: Inventory items
- **When to modify**: New business rules, validations

#### `UI/`
- **Purpose**: User interface components
- **Files**:
  - `main_window.py`: Main application window
  - `dashboard.py`, `students.py`, etc.: Tab implementations
  - `dialogs.py`: Modal dialogs
- **When to modify**: UI changes, new features, user workflows

#### `utils/`
- **Purpose**: Utility functions
- **Files**:
  - `helpers.py`: Common functions
  - `validators.py`: Validation utilities
  - `export_import.py`: Data import/export
- **When to modify**: New utilities, helper functions

---

## Code Style & Conventions

### Python Style Guide (PEP 8)

#### Import Organization
```python
# 1. Standard library
import os
import sys
from datetime import date, datetime
from typing import Optional, List, Dict

# 2. Third-party libraries
import mysql.connector
from tkinter import ttk

# 3. Local application
import config
from database.connection import db
from models.student import Student
```

#### Naming Conventions
```python
# Classes: PascalCase
class StudentDialog:
    pass

# Functions: snake_case
def validate_student_data():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_STUDENT_AGE = 18
MIN_STUDENT_AGE = 3

# Private variables: _leading_underscore
_connection_pool = None
```

#### Type Hints
```python
def calculate_student_balance(
    student_id: int,
    academic_year: str
) -> float:
    """Calculate total balance for student."""
    pass

def get_students(
    class_name: str
) -> List[Dict[str, Any]]:
    """Retrieve students in class."""
    pass
```

#### Docstrings (Google Style)
```python
def record_payment(
    student_id: int,
    amount: float,
    payment_date: Optional[date] = None
) -> tuple[bool, str]:
    """Record a fee payment for a student.
    
    Args:
        student_id: ID of student making payment
        amount: Payment amount in currency
        payment_date: Date of payment (defaults to today)
    
    Returns:
        Tuple of (success: bool, message: str)
        - success: True if payment recorded
        - message: Detailed status message
    
    Raises:
        ValueError: If student_id is invalid
        Exception: If database error occurs
    
    Example:
        >>> success, msg = record_payment(1, 25000.00)
        >>> if success:
        ...     print(f"Payment recorded: {msg}")
    """
    pass
```

---

## Adding New Features

### Feature Development Checklist

### 1. Define the Model

Create new model in `models/`:

```python
# models/new_feature.py
"""New feature models."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import config
from database.connection import db

@dataclass
class NewFeature:
    """Represents a new feature entity."""
    
    feature_id: Optional[int] = None
    name: str = ""
    description: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def validate(self) -> tuple[bool, str]:
        """Validate feature data."""
        if not self.name.strip():
            return False, "Name is required"
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save to database."""
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
            if self.feature_id:
                query = """
                    UPDATE new_feature_table 
                    SET name=%s, description=%s, is_active=%s
                    WHERE feature_id=%s
                """
                params = (self.name, self.description, self.is_active, self.feature_id)
                db.execute_query(query, params)
                return True, "Updated successfully"
            else:
                query = """
                    INSERT INTO new_feature_table (name, description, is_active)
                    VALUES (%s, %s, %s)
                """
                params = (self.name, self.description, self.is_active)
                self.feature_id = db.execute_query(query, params)
                return True, f"Created with ID {self.feature_id}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @classmethod
    def get_all(cls) -> List['NewFeature']:
        """Get all features."""
        query = "SELECT * FROM new_feature_table WHERE is_active=1"
        results = db.execute_query(query, fetch=True)
        return [cls(**row) for row in results] if results else []
```

### 2. Add Database Queries

Update `database/queries.py`:

```python
class Queries:
    # Existing queries...
    
    GET_NEW_FEATURES = """
        SELECT * FROM new_feature_table
        WHERE is_active = 1
        ORDER BY name
    """
    
    SEARCH_NEW_FEATURES = """
        SELECT * FROM new_feature_table
        WHERE name LIKE %s OR description LIKE %s
        ORDER BY name
    """
```

### 3. Add Database Schema

Update `database/schema.sql`:

```sql
CREATE TABLE new_feature_table (
    feature_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_name (name),
    INDEX idx_active (is_active)
);
```

### 4. Create UI Tab

Create `UI/new_feature.py`:

```python
"""New feature UI tab."""
import tkinter as tk
from tkinter import ttk, messagebox
from models.new_feature import NewFeature
from UI.dialogs import BaseDialog

class NewFeatureTab:
    """UI for new feature management."""
    
    def __init__(self, parent, role='Administrator'):
        self.parent = parent
        self.role = role
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup UI components."""
        # Create main frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill='both', expand=True)
        
        # Header
        header = ttk.Label(self.frame, text="New Feature", 
                          font=('Arial', 16, 'bold'))
        header.pack(pady=10)
        
        # Button frame
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Add New", 
                  command=self.add_new).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Edit", 
                  command=self.edit).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete", 
                  command=self.delete).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Refresh", 
                  command=self.load_data).pack(side='left', padx=5)
        
        # Treeview
        cols = ('ID', 'Name', 'Description', 'Status')
        self.tree = ttk.Treeview(self.frame, columns=cols, show='headings', height=15)
        
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)
    
    def load_data(self):
        """Load data from database."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Fetch data
        features = NewFeature.get_all()
        for feature in features:
            self.tree.insert('', 'end', values=(
                feature.feature_id,
                feature.name,
                feature.description[:50],  # Truncate
                "Active" if feature.is_active else "Inactive"
            ))
    
    def add_new(self):
        """Add new feature."""
        dialog = NewFeatureDialog(self.parent)
        if dialog.show():
            feature = dialog.get_result()
            success, message = feature.save()
            if success:
                messagebox.showinfo("Success", message)
                self.load_data()
            else:
                messagebox.showerror("Error", message)
    
    def edit(self):
        """Edit selected feature."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a feature to edit")
            return
        
        feature_id = self.tree.item(selection[0])['values'][0]
        # Load and edit...
    
    def delete(self):
        """Delete selected feature."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Select a feature to delete")
            return
        
        if messagebox.askyesno("Confirm", "Delete selected feature?"):
            # Delete logic...
            self.load_data()
```

### 5. Add Dialog

Update `UI/dialogs.py`:

```python
class NewFeatureDialog(BaseDialog):
    """Dialog for adding/editing features."""
    
    def __init__(self, parent, feature=None):
        super().__init__(parent, "New Feature", 400, 250)
        self.feature = feature
        self.setup_ui()
        if feature:
            self.load_feature_data()
    
    def setup_ui(self):
        """Setup dialog UI."""
        frame = self.main_frame
        
        # Name
        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.name_var, width=30).grid(row=0, column=1, pady=5)
        
        # Description
        ttk.Label(frame, text="Description:").grid(row=1, column=0, sticky='nw', pady=5)
        self.desc_text = tk.Text(frame, height=4, width=30)
        self.desc_text.grid(row=1, column=1, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Save", command=self.on_ok).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side='left', padx=5)
    
    def load_feature_data(self):
        """Load feature data into form."""
        self.name_var.set(self.feature.name)
        self.desc_text.insert('1.0', self.feature.description)
    
    def get_result(self):
        """Get form result as Feature object."""
        return NewFeature(
            feature_id=self.feature.feature_id if self.feature else None,
            name=self.name_var.get(),
            description=self.desc_text.get('1.0', 'end-1c'),
            is_active=True
        )
```

### 6. Register in Main Window

Update `UI/main_window.py`:

```python
def create_tabs(self):
    """Create tabs based on user permissions."""
    tabs_to_create = [
        ('dashboard', 'Dashboard', DashboardTab),
        ('students', 'Students', StudentsTab),
        ('new_feature', 'New Feature', NewFeatureTab),  # Add this
        # ... other tabs
    ]
    
    for feature, label, TabClass in tabs_to_create:
        if config.Config.has_permission(feature):
            tab = TabClass(self.notebook, self.role)
            self.notebook.add(tab.frame, text=label)
```

### 7. Register Permissions

Update `config.py`:

```python
PERMISSIONS = {
    'Administrator': {
        'dashboard', 'students', 'teachers', 'new_feature',
        # ... other features
    },
    'Headteacher': {
        'dashboard', 'students', 'new_feature',
        # ...
    }
}
```

### 8. Write Tests

Create `tests/test_new_feature.py`:

```python
"""Tests for new feature."""
import unittest
from datetime import datetime
from models.new_feature import NewFeature

class TestNewFeature(unittest.TestCase):
    """Test cases for NewFeature model."""
    
    def test_validation_required_fields(self):
        """Test validation requires name."""
        feature = NewFeature(name="")
        is_valid, message = feature.validate()
        self.assertFalse(is_valid)
        self.assertIn("required", message.lower())
    
    def test_validation_passes(self):
        """Test validation passes with valid data."""
        feature = NewFeature(name="Test Feature")
        is_valid, message = feature.validate()
        self.assertTrue(is_valid)
    
    def test_save_creates_new_feature(self):
        """Test saving creates new feature."""
        feature = NewFeature(
            name="Test Feature",
            description="Test Description"
        )
        success, message = feature.save()
        self.assertTrue(success)
        self.assertIsNotNone(feature.feature_id)

if __name__ == '__main__':
    unittest.main()
```

---

## Testing Guidelines

### Unit Testing

```python
import unittest
from models.student import Student

class TestStudentModel(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.student = Student(
            first_name="John",
            last_name="Doe",
            class_name="Grade 1",
            enrollment_date=date(2025, 1, 15)
        )
    
    def test_validate_success(self):
        """Test successful validation."""
        is_valid, msg = self.student.validate()
        self.assertTrue(is_valid)
    
    def test_validate_missing_name(self):
        """Test validation fails with missing name."""
        self.student.first_name = ""
        is_valid, msg = self.student.validate()
        self.assertFalse(is_valid)
```

### Integration Testing

```python
def test_student_save_and_retrieve():
    """Test saving and retrieving student."""
    # Create
    student = Student(first_name="Jane", last_name="Smith", ...)
    success, msg = student.save()
    assert success
    student_id = student.student_id
    
    # Retrieve
    retrieved = Student.get_by_id(student_id)
    assert retrieved.first_name == "Jane"
```

### Running Tests

```bash
# Run all tests (no database needed: tests/_support.py fakes it)
python -m unittest discover -s tests -t .

# Run one test module
python -m unittest tests.test_config_auth
```

---

## Debugging Tips

### Enable Logging

```python
import logging

# Setup detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Log database queries
logger.debug(f"Executing query: {query}")
logger.debug(f"Parameters: {params}")
```

### Database Debugging

```python
# Check active connections
mysql> SHOW PROCESSLIST;

# Check table structure
mysql> DESCRIBE students;

# Debug slow queries
mysql> SET GLOBAL slow_query_log = 'ON';
```

### UI Debugging

```python
# Add debug prints
print(f"DEBUG: Tab created - {tab_name}")

# Break on exception
import traceback
try:
    # Code
except Exception as e:
    traceback.print_exc()
```

### Common Issues

**Database Connection Failed**
```python
# Check config
from config import Config
print(Config.DB_CONFIG)

# Test connection
from database.connection import DatabaseConnection
db = DatabaseConnection()
print(db.test_connection())
```

**UI Widget Not Appearing**
```python
# Ensure pack/grid is called
self.widget.pack()  # or .grid()

# Check visibility
print(self.widget.winfo_width())  # Should be > 1
```

**Data Not Saving**
```python
# Check transaction commit
connection.commit()  # Must be called

# Verify parameters
print(f"Query: {query}")
print(f"Params: {params}")
```

---

## Database Migration

### Creating a Migration

1. **Backup current database**
   ```bash
   python scripts/backup_database.py
   ```

2. **Create migration script** (`scripts/migrate_vXX.py`)
   ```python
   """Migration: Add new column to students table."""
   from database.connection import DatabaseConnection
   
   def migrate():
       db = DatabaseConnection()
       try:
           # Add new column
           db.execute_query("""
               ALTER TABLE students 
               ADD COLUMN new_field VARCHAR(100)
           """)
           print("Migration successful")
           return True
       except Exception as e:
           print(f"Migration failed: {e}")
           return False
   
   if __name__ == '__main__':
       migrate()
   ```

3. **Run migration**
   ```bash
   python scripts/migrate_vXX.py
   ```

4. **Update schema.sql**
   ```sql
   ALTER TABLE students ADD COLUMN new_field VARCHAR(100);
   ```

### Rollback Procedure

```sql
-- Undo migration
ALTER TABLE students DROP COLUMN new_field;

-- Or restore from backup
python scripts/restore_database.py backup_20250115_000000.sql
```

---

## Version Control Workflow

### Branch Naming
```
feature/feature-name      # New features
bugfix/bug-description    # Bug fixes
hotfix/issue-fix         # Critical fixes
docs/documentation       # Documentation updates
```

### Commit Message Format
```
<type>: <subject>

<body>

<footer>

Types: feat, fix, docs, style, refactor, test, chore
```

### Example Workflow
```bash
# Create feature branch
git checkout -b feature/new-report-type

# Make changes
git add .
git commit -m "feat: Add new report type for expense analysis"

# Push and create PR
git push origin feature/new-report-type

# After review, merge
git merge --no-ff feature/new-report-type
```

---

## Performance Optimization

### Database Optimization

1. **Add Indexes**
   ```sql
   CREATE INDEX idx_student_class ON students(class_name);
   CREATE INDEX idx_fee_date ON student_fees(payment_date);
   ```

2. **Optimize Queries**
   ```python
   # Bad: Multiple queries
   for student in students:
       balance = db.execute_query("SELECT SUM(...) WHERE student_id=%s", (student['id'],))
   
   # Good: Single query with JOIN
   db.execute_query("""
       SELECT s.*, SUM(sf.amount_paid) as total
       FROM students s
       LEFT JOIN student_fees sf ON s.id = sf.student_id
       GROUP BY s.id
   """)
   ```

3. **Use Pagination**
   ```python
   LIMIT 1000 OFFSET 0  # Load first 1000 records
   ```

### UI Optimization

1. **Lazy Load**
   ```python
   def on_tab_focus(self):
       """Load data only when tab is visible."""
       if not self.data_loaded:
           self.load_data()
           self.data_loaded = True
   ```

2. **Debounce Search**
   ```python
   def on_search_input(self, event):
       if hasattr(self, 'search_timer'):
           self.root.after_cancel(self.search_timer)
       self.search_timer = self.root.after(500, self.execute_search)
   ```

---

## Common Pitfalls

### 1. Not Closing Connections
```python
# Bad
connection = db.get_connection()
cursor = connection.cursor()
cursor.execute(query)

# Good
connection = None
cursor = None
try:
    connection = db.get_connection()
    cursor = connection.cursor()
    cursor.execute(query)
finally:
    if cursor:
        cursor.close()
    if connection:
        connection.close()
```

### 2. Incorrect Parameter Binding
```python
# Bad (SQL injection vulnerable)
query = f"SELECT * FROM students WHERE class = '{class_name}'"

# Good
query = "SELECT * FROM students WHERE class = %s"
db.execute_query(query, (class_name,))
```

### 3. Missing Error Handling
```python
# Bad
balance = float(self.amount_var.get())

# Good
try:
    balance = float(self.amount_var.get())
except ValueError:
    messagebox.showerror("Error", "Invalid amount")
```

### 4. Not Validating Input
```python
# Bad
email = self.email_entry.get()
# Use directly

# Good
if not Validators.validate_email(email):
    messagebox.showerror("Error", "Invalid email")
    return
```

### 5. Hardcoded Values
```python
# Bad
MAX_STUDENTS = 500
TERM_END_DATE = "2025-03-31"

# Good
MAX_STUDENTS = config.Config.MAX_STUDENTS
TERM_END_DATE = config.Config.TERM_END_DATE
```

---

## Development Resources

### Documentation
- [Python Docs](https://docs.python.org/3/)
- [Tkinter Docs](https://docs.python.org/3/library/tkinter.html)
- [MySQL Docs](https://dev.mysql.com/doc/)
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)

### Tools
- IDE: PyCharm, VS Code, Visual Studio
- Database: MySQL Workbench, DBeaver
- Version Control: Git, GitHub
- Testing: pytest, unittest

---

**Document Version**: 1.0  
**Last Updated**: January 2026


## Storage backends (SQLite and MySQL)

The program stores data either in a single SQLite file on the computer (the default, chosen on the
first-launch Welcome screen) or on a MySQL server. `config.Config.DB_BACKEND` holds the choice
(`"sqlite"` / `"mysql"`); installs whose settings predate SQLite support resolve to MySQL.

- All code uses `from database.connection import db`; it forwards to `database/sqlite_backend.py` or
  `database/mysql_backend.py`. Nothing connects until first use.
- Write SQL in MySQL dialect with `%s` placeholders. On SQLite the backend translates placeholders,
  `%%` and `INSERT IGNORE`, and provides `CONCAT`, `YEAR`, `MONTH`, `DAY`, `CURDATE`, `NOW` and
  `DATE_FORMAT` with MySQL semantics.
- Constructs that differ between the dialects go through helpers instead of raw SQL:
  `db.group_concat_distinct(expr, "', '")`, `db.upsert_clause(conflict_cols, set_new=..., set_sql=...)`,
  `db.column_exists(table, col)`, `db.table_exists(table)`, `db.list_tables()`.
- Use `* 100.0 / COUNT(*)` rather than `/ COUNT(*) * 100`: SQLite divides integers exactly like Python 2.
- Schemas: `database/schema.sql` (MySQL) and `database/schema_sqlite.sql` (SQLite) must stay in step.
  SQLite files are created and upgraded automatically (`PRAGMA user_version`; bump `SCHEMA_VERSION`
  and add a step to `_MIGRATIONS` in `sqlite_backend.py`). For MySQL add an idempotent step to
  `apply_db_changes.py`. Runtime `CREATE TABLE`/`ALTER` code must be skipped when `db.manages_schema`.
- `scripts/mysql_to_sqlite.py [--switch]` copies a MySQL installation into a new SQLite file.
- `tests/test_sqlite_integration.py` runs the real models, rollover, payroll, reports and backup code
  against a temporary SQLite file; no server is needed for any test.
