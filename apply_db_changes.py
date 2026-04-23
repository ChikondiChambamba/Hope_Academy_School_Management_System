#!/usr/bin/env python3
"""Apply database schema changes"""
from database.connection import db

# Add salary column to teachers
try:
    db.execute_query('ALTER TABLE teachers ADD COLUMN salary_amount DECIMAL(10,2) DEFAULT 0.00')
    print('OK Added salary_amount column to teachers')
except Exception as e:
    if 'Duplicate column' in str(e):
        print('OK salary_amount already exists')
    else:
        print(f'ERR {e}')

# Add is_new column to students
try:
    db.execute_query('ALTER TABLE students ADD COLUMN is_new BOOLEAN DEFAULT TRUE')
    print('OK Added is_new column to students')
except Exception as e:
    if 'Duplicate column' in str(e):
        print('OK is_new already exists')
    else:
        print(f'ERR {e}')

# Add allowance column to teachers
try:
    db.execute_query('ALTER TABLE teachers ADD COLUMN allowance_amount DECIMAL(10,2) DEFAULT 0.00')
    print('OK Added allowance_amount column to teachers')
except Exception as e:
    if 'Duplicate column' in str(e):
        print('OK allowance_amount already exists')
    else:
        print(f'ERR {e}')

# Add performance indexes
try:
    db.execute_query('CREATE INDEX idx_student_fees_student_fee_type ON student_fees (student_id, fee_type_id)')
    print('OK Added idx_student_fees_student_fee_type')
except Exception as e:
    if 'Duplicate' in str(e) or 'exists' in str(e):
        print('OK idx_student_fees_student_fee_type already exists')
    else:
        print(f'ERR {e}')

try:
    db.execute_query('CREATE INDEX idx_student_fees_fee_type ON student_fees (fee_type_id)')
    print('OK Added idx_student_fees_fee_type')
except Exception as e:
    if 'Duplicate' in str(e) or 'exists' in str(e):
        print('OK idx_student_fees_fee_type already exists')
    else:
        print(f'ERR {e}')

try:
    db.execute_query('CREATE INDEX idx_fee_types_year_term ON fee_types (academic_year, term)')
    print('OK Added idx_fee_types_year_term')
except Exception as e:
    if 'Duplicate' in str(e) or 'exists' in str(e):
        print('OK idx_fee_types_year_term already exists')
    else:
        print(f'ERR {e}')

# Create teacher advances table
try:
    db.execute_query("""
        CREATE TABLE teacher_salary_advances (
            advance_id INT PRIMARY KEY AUTO_INCREMENT,
            teacher_id INT NOT NULL,
            advance_amount DECIMAL(10,2) NOT NULL,
            advance_date DATE NOT NULL,
            description VARCHAR(255),
            status ENUM('Pending', 'Approved', 'Deducted') DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
            INDEX idx_teacher_id (teacher_id),
            INDEX idx_advance_date (advance_date),
            INDEX idx_status (status)
        )
    """)
    print('OK Created teacher_salary_advances table')
except Exception as e:
    if 'already exists' in str(e):
        print('OK teacher_salary_advances table already exists')
    else:
        print(f'ERR {e}')

print('\nDatabase changes applied successfully!')
