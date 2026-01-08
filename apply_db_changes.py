#!/usr/bin/env python3
"""Apply database schema changes for teacher salary feature"""
from database.connection import db

# Add salary column to teachers
try:
    db.execute_query('ALTER TABLE teachers ADD COLUMN salary_amount DECIMAL(10,2) DEFAULT 0.00')
    print("✓ Added salary_amount column to teachers")
except Exception as e:
    if "Duplicate column" in str(e):
        print("✓ salary_amount already exists")
    else:
        print(f"✗ Error: {e}")

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
    print("✓ Created teacher_salary_advances table")
except Exception as e:
    if "already exists" in str(e):
        print("✓ teacher_salary_advances table already exists")
    else:
        print(f"✗ Error: {e}")

print("\nDatabase changes applied successfully!")
