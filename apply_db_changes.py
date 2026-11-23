#!/usr/bin/env python3
"""Bring an existing database up to date with database/schema.sql.

Every migration is idempotent, so the script is safe to run repeatedly.
Fresh installs do not need it: setup_database.py already creates the full schema.
"""
import sys

from database.connection import db

PAYMENT_METHODS = "ENUM('Cash', 'Mobile money', 'M-Pesa', 'Bank Transfer', 'Check', 'Other') DEFAULT 'Cash'"


def _column_exists(table: str, column: str) -> bool:
    rows = db.execute_query(
        "SELECT 1 FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, column), fetch=True)
    return bool(rows)


def _index_exists(table: str, index: str) -> bool:
    rows = db.execute_query(
        "SELECT 1 FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s",
        (table, index), fetch=True)
    return bool(rows)


def add_column(table: str, column: str, definition: str):
    def run():
        if _column_exists(table, column):
            return f"{table}.{column} already exists"
        db.execute_query(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return f"added {table}.{column}"
    return run


def add_index(table: str, index: str, columns: str):
    def run():
        if _index_exists(table, index):
            return f"{index} already exists"
        db.execute_query(f"CREATE INDEX {index} ON {table} ({columns})")
        return f"added {index}"
    return run


def widen_payment_methods():
    # The UI offers 'Mobile money'; older databases only allowed 'M-Pesa', so under
    # STRICT_TRANS_TABLES every Mobile money payment/expense insert was rejected.
    # 'M-Pesa' is kept so existing rows (if any) remain valid.
    for table in ("student_fees", "expenses"):
        db.execute_query(f"ALTER TABLE {table} MODIFY COLUMN payment_method {PAYMENT_METHODS}")
    return "payment_method accepts 'Mobile money' on student_fees and expenses"


def create_table(name: str, ddl: str):
    def run():
        db.execute_query(ddl)
        return f"ensured table {name}"
    return run


def ensure_fee_rule_columns():
    from models.finance import FeeType
    FeeType.ensure_fee_rule_columns()
    return "ensured fee_types.new_students_only (registration/uniform fees flagged once)"


def ensure_expense_terms():
    from models.finance import Expense
    Expense.ensure_term_columns()
    return "ensured expenses academic_year/term columns and index"


def normalize_fee_type_terms():
    from models.finance import FeeType
    FeeType.ensure_term_labels()
    return "normalized legacy fee type term labels"


MIGRATIONS = [
    add_column("teachers", "salary_amount", "DECIMAL(10,2) DEFAULT 0.00"),
    add_column("teachers", "allowance_amount", "DECIMAL(10,2) DEFAULT 0.00"),
    add_column("students", "is_new", "BOOLEAN DEFAULT TRUE"),
    add_index("student_fees", "idx_student_fees_student_fee_type", "student_id, fee_type_id"),
    add_index("student_fees", "idx_student_fees_fee_type", "fee_type_id"),
    add_index("fee_types", "idx_fee_types_year_term", "academic_year, term"),
    ensure_expense_terms,
    ensure_fee_rule_columns,
    normalize_fee_type_terms,
    widen_payment_methods,
    # Rollovers from the last term open the next academic year; record both years.
    add_column("term_rollover_runs", "to_academic_year", "VARCHAR(32) NULL AFTER to_term"),
    add_column("term_changes", "previous_academic_year", "VARCHAR(32) NULL AFTER academic_year"),
    create_table("teacher_salary_advances", """
        CREATE TABLE IF NOT EXISTS teacher_salary_advances (
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
        )"""),
    # Defined after the broken sample-data block in older schema.sql files, so
    # databases created from them never got it and audit writes failed silently.
    create_table("audit_log", """
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INT PRIMARY KEY AUTO_INCREMENT,
            timestamp DATETIME NOT NULL,
            action VARCHAR(100) NOT NULL,
            user VARCHAR(100),
            entity_type VARCHAR(50),
            entity_id VARCHAR(50),
            status VARCHAR(20) DEFAULT 'SUCCESS',
            details JSON,
            error_message TEXT,
            ip_address VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_timestamp (timestamp),
            INDEX idx_user (user),
            INDEX idx_action (action),
            INDEX idx_entity (entity_type, entity_id)
        )"""),
]


def main() -> int:
    if db.manages_schema:
        print("This installation stores data on this computer (SQLite). Its database is created "
              "and upgraded automatically when the program starts; nothing to do.")
        return 0
    failures = 0
    for migration in MIGRATIONS:
        try:
            print(f"OK  {migration()}")
        except Exception as e:
            failures += 1
            print(f"ERR {getattr(migration, '__name__', migration)}: {e}")
    if failures:
        print(f"\n{failures} migration(s) failed.")
        return 1
    print("\nDatabase is up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
