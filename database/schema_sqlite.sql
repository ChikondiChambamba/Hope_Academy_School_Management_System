-- Hope Academy School Management System - SQLite schema
--
-- Applied automatically the first time the application starts with
-- "On this computer" storage. Keep in step with database/schema.sql (MySQL);
-- when changing it, bump SCHEMA_VERSION in database/sqlite_backend.py and add
-- an upgrade step there.
--
-- Conventions that keep behaviour identical to MySQL:
--   * text columns COLLATE NOCASE   - MySQL's default collation is case-insensitive
--   * DATE / TIMESTAMP declared types - returned to Python as date / datetime
--   * datetime('now','localtime')   - MySQL CURRENT_TIMESTAMP is local time
--   * CHECK (...) IN (...)          - replaces MySQL ENUM

PRAGMA foreign_keys = ON;

CREATE TABLE students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code TEXT COLLATE NOCASE NOT NULL UNIQUE,
    first_name TEXT COLLATE NOCASE NOT NULL,
    last_name TEXT COLLATE NOCASE NOT NULL,
    class TEXT COLLATE NOCASE NOT NULL,
    birth_date DATE,
    parent_name TEXT COLLATE NOCASE,
    parent_phone TEXT,
    parent_email TEXT COLLATE NOCASE,
    address TEXT,
    enrollment_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    is_new BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_students_class ON students (class);
CREATE INDEX idx_students_last_name ON students (last_name);
CREATE INDEX idx_students_active ON students (is_active);

CREATE TABLE teachers (
    teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_code TEXT COLLATE NOCASE NOT NULL UNIQUE,
    first_name TEXT COLLATE NOCASE NOT NULL,
    last_name TEXT COLLATE NOCASE NOT NULL,
    phone TEXT,
    email TEXT COLLATE NOCASE,
    subject_specialization TEXT COLLATE NOCASE,
    hire_date DATE NOT NULL,
    salary_amount DECIMAL(10,2) DEFAULT 0.00,
    allowance_amount DECIMAL(10,2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_teachers_last_name ON teachers (last_name);
CREATE INDEX idx_teachers_active ON teachers (is_active);

CREATE TABLE fee_types (
    fee_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fee_name TEXT COLLATE NOCASE NOT NULL,
    description TEXT,
    amount DECIMAL(10,2) NOT NULL,
    term TEXT COLLATE NOCASE,
    academic_year TEXT COLLATE NOCASE NOT NULL,
    is_required BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_fee_types_year_term ON fee_types (academic_year, term);

CREATE TABLE student_fees (
    fee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    fee_type_id INTEGER NOT NULL REFERENCES fee_types(fee_type_id) ON DELETE CASCADE,
    amount_paid DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_method TEXT COLLATE NOCASE DEFAULT 'Cash'
        CHECK (payment_method IN ('Cash', 'Mobile money', 'M-Pesa', 'Bank Transfer', 'Check', 'Other')),
    receipt_number TEXT COLLATE NOCASE UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_student_fees_student_fee_type ON student_fees (student_id, fee_type_id);
CREATE INDEX idx_student_fees_fee_type ON student_fees (fee_type_id);
CREATE INDEX idx_student_fees_payment_date ON student_fees (payment_date);

CREATE TABLE receipt_sequence (
    seq_date TEXT PRIMARY KEY,
    seq INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE student_fee_exemptions (
    exemption_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    fee_type_id INTEGER NOT NULL REFERENCES fee_types(fee_type_id) ON DELETE CASCADE,
    reason TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    UNIQUE (student_id, fee_type_id)
);

CREATE TABLE term_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    academic_year TEXT COLLATE NOCASE NOT NULL,     -- year of the term that was opened
    previous_academic_year TEXT COLLATE NOCASE,     -- year of the term that was closed
    previous_term TEXT COLLATE NOCASE,
    term_name TEXT COLLATE NOCASE NOT NULL,
    start_date DATE,
    rollover_processed BOOLEAN DEFAULT 0,
    changed_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_term_change_year_term ON term_changes (academic_year, term_name);

CREATE TABLE student_term_fee_rollovers (
    rollover_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    from_academic_year TEXT COLLATE NOCASE NOT NULL,
    from_term TEXT COLLATE NOCASE NOT NULL,
    to_academic_year TEXT COLLATE NOCASE NOT NULL,
    to_term TEXT COLLATE NOCASE NOT NULL,
    carried_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
    source_total_due DECIMAL(12,2) NOT NULL DEFAULT 0,
    source_total_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
    computed_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    UNIQUE (student_id, to_academic_year, to_term)
);
CREATE INDEX idx_rollover_target ON student_term_fee_rollovers (to_academic_year, to_term);
CREATE INDEX idx_rollover_source ON student_term_fee_rollovers (from_academic_year, from_term);

CREATE TABLE term_rollover_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    academic_year TEXT COLLATE NOCASE NOT NULL,     -- year of from_term
    from_term TEXT COLLATE NOCASE NOT NULL,
    to_term TEXT COLLATE NOCASE NOT NULL,
    to_academic_year TEXT COLLATE NOCASE,           -- year of to_term
    status TEXT NOT NULL DEFAULT 'PREVIEW',
    total_students INTEGER NOT NULL DEFAULT 0,
    reset_students INTEGER NOT NULL DEFAULT 0,
    carry_students INTEGER NOT NULL DEFAULT 0,
    previous_outstanding_total DECIMAL(12,2) NOT NULL DEFAULT 0,
    new_term_total DECIMAL(12,2) NOT NULL DEFAULT 0,
    carry_forward_total DECIMAL(12,2) NOT NULL DEFAULT 0,
    opening_balance_total DECIMAL(12,2) NOT NULL DEFAULT 0,
    executed_by TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    completed_at TIMESTAMP
);
CREATE INDEX idx_rollover_run_lookup ON term_rollover_runs (academic_year, from_term, to_term, status);

CREATE TABLE term_rollover_run_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES term_rollover_runs(run_id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    student_code TEXT,
    student_name TEXT,
    class_name TEXT,
    previous_outstanding DECIMAL(12,2) NOT NULL DEFAULT 0,
    new_term_total DECIMAL(12,2) NOT NULL DEFAULT 0,
    carry_forward_total DECIMAL(12,2) NOT NULL DEFAULT 0,
    reset_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    opening_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
    payment_status TEXT NOT NULL DEFAULT 'Paid',
    carry_status TEXT NOT NULL DEFAULT 'Reset',
    details_json TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, student_id)
);
CREATE INDEX idx_rollover_item_student ON term_rollover_run_items (student_id);

CREATE TABLE student_term_fee_rollover_items (
    rollover_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    from_academic_year TEXT COLLATE NOCASE NOT NULL,
    from_term TEXT COLLATE NOCASE NOT NULL,
    to_academic_year TEXT COLLATE NOCASE NOT NULL,
    to_term TEXT COLLATE NOCASE NOT NULL,
    source_fee_type_id INTEGER,
    source_fee_name TEXT COLLATE NOCASE NOT NULL,
    source_is_required BOOLEAN DEFAULT 1,
    source_is_class_specific BOOLEAN DEFAULT 0,
    source_expected_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    source_paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    carried_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    source_status TEXT NOT NULL DEFAULT 'Paid',
    target_fee_type_id INTEGER,
    target_fee_name TEXT,
    target_applicable BOOLEAN DEFAULT 0,
    run_id INTEGER,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    UNIQUE (student_id, from_academic_year, from_term, to_academic_year, to_term, source_fee_name)
);
CREATE INDEX idx_rollover_items_target ON student_term_fee_rollover_items (to_academic_year, to_term);
CREATE INDEX idx_rollover_items_student ON student_term_fee_rollover_items (student_id);

CREATE TABLE teacher_salary_advances (
    advance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    advance_amount DECIMAL(10,2) NOT NULL,
    advance_date DATE NOT NULL,
    description TEXT,
    status TEXT COLLATE NOCASE DEFAULT 'Pending' CHECK (status IN ('Pending', 'Approved', 'Deducted')),
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_advances_teacher ON teacher_salary_advances (teacher_id);
CREATE INDEX idx_advances_date ON teacher_salary_advances (advance_date);

CREATE TABLE teacher_salary_monthly (
    payroll_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    payroll_month TEXT NOT NULL,
    base_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
    allowance_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    advances_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    gross_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
    net_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
    is_paid BOOLEAN NOT NULL DEFAULT 0,
    generated_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    UNIQUE (teacher_id, payroll_month)
);
CREATE INDEX idx_salary_month ON teacher_salary_monthly (payroll_month);

CREATE TABLE inventory_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_code TEXT COLLATE NOCASE NOT NULL UNIQUE,
    item_name TEXT COLLATE NOCASE NOT NULL,
    category TEXT COLLATE NOCASE,
    quantity INTEGER DEFAULT 0,
    unit_price DECIMAL(10,2),
    total_value DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    min_quantity INTEGER DEFAULT 10,
    max_quantity INTEGER DEFAULT 100,
    location TEXT,
    supplier TEXT COLLATE NOCASE,
    last_restocked DATE,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_inventory_category ON inventory_items (category);
CREATE INDEX idx_inventory_quantity ON inventory_items (quantity);

CREATE TABLE expenses (
    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_date DATE NOT NULL,
    item_id INTEGER REFERENCES inventory_items(item_id) ON DELETE SET NULL,
    description TEXT COLLATE NOCASE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    category TEXT COLLATE NOCASE,
    academic_year TEXT COLLATE NOCASE,
    term TEXT COLLATE NOCASE,
    payment_method TEXT COLLATE NOCASE DEFAULT 'Cash'
        CHECK (payment_method IN ('Cash', 'Mobile money', 'M-Pesa', 'Bank Transfer', 'Check', 'Other')),
    receipt_number TEXT COLLATE NOCASE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_expenses_date ON expenses (expense_date);
CREATE INDEX idx_expenses_year_term ON expenses (academic_year, term);
CREATE INDEX idx_expenses_category ON expenses (category);
CREATE INDEX idx_expenses_receipt ON expenses (receipt_number);

CREATE TABLE expense_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT COLLATE NOCASE NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    attendance_date DATE NOT NULL,
    status TEXT COLLATE NOCASE DEFAULT 'Present' CHECK (status IN ('Present', 'Absent', 'Late', 'Excused')),
    check_in_time TEXT,
    check_out_time TEXT,
    remarks TEXT,
    recorded_by TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    UNIQUE (student_id, attendance_date)
);
CREATE INDEX idx_attendance_date ON attendance (attendance_date);
CREATE INDEX idx_attendance_status ON attendance (status);

CREATE TABLE classes (
    class_id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name TEXT COLLATE NOCASE NOT NULL UNIQUE,
    teacher_id INTEGER REFERENCES teachers(teacher_id) ON DELETE SET NULL,
    room_number TEXT,
    academic_year TEXT COLLATE NOCASE,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE student_classes (
    student_class_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    academic_year TEXT COLLATE NOCASE NOT NULL,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    UNIQUE (student_id, class_id, academic_year)
);
CREATE INDEX idx_student_classes_class ON student_classes (class_id);

CREATE TABLE fee_type_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fee_type_id INTEGER NOT NULL REFERENCES fee_types(fee_type_id) ON DELETE CASCADE,
    class_id INTEGER NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    academic_year TEXT COLLATE NOCASE,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    UNIQUE (fee_type_id, class_id)
);

CREATE TABLE student_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    action TEXT,
    changed_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
    changed_by TEXT,
    old_data TEXT,
    new_data TEXT
);

CREATE TABLE audit_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    action TEXT NOT NULL,
    user TEXT,
    entity_type TEXT,
    entity_id TEXT,
    status TEXT DEFAULT 'SUCCESS',
    details TEXT,
    error_message TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX idx_audit_timestamp ON audit_log (timestamp);
CREATE INDEX idx_audit_user ON audit_log (user);
CREATE INDEX idx_audit_action ON audit_log (action);
CREATE INDEX idx_audit_entity ON audit_log (entity_type, entity_id);

-- Views (same results as the MySQL views)
CREATE VIEW daily_attendance_summary AS
SELECT
    attendance_date,
    COUNT(*) AS total_students,
    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
    SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
    SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) AS late_count,
    SUM(CASE WHEN status = 'Excused' THEN 1 ELSE 0 END) AS excused_count,
    ROUND(SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS attendance_rate
FROM attendance
GROUP BY attendance_date;

CREATE VIEW low_stock_items AS
SELECT item_id, item_code, item_name, category, quantity, min_quantity, unit_price, total_value,
       (min_quantity - quantity) AS reorder_quantity
FROM inventory_items
WHERE quantity < min_quantity;

CREATE VIEW financial_summary AS
SELECT CAST(strftime('%Y', payment_date) AS INTEGER) AS year,
       CAST(strftime('%m', payment_date) AS INTEGER) AS month,
       'Revenue' AS type,
       SUM(amount_paid) AS amount
FROM student_fees
GROUP BY 1, 2
UNION ALL
SELECT CAST(strftime('%Y', expense_date) AS INTEGER),
       CAST(strftime('%m', expense_date) AS INTEGER),
       'Expense',
       SUM(amount)
FROM expenses
GROUP BY 1, 2;

-- Keep updated_at current (MySQL: ON UPDATE CURRENT_TIMESTAMP)
CREATE TRIGGER students_updated_at AFTER UPDATE ON students
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE students SET updated_at = datetime('now', 'localtime') WHERE student_id = NEW.student_id;
END;

CREATE TRIGGER teachers_updated_at AFTER UPDATE ON teachers
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE teachers SET updated_at = datetime('now', 'localtime') WHERE teacher_id = NEW.teacher_id;
END;

CREATE TRIGGER inventory_updated_at AFTER UPDATE ON inventory_items
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE inventory_items SET updated_at = datetime('now', 'localtime') WHERE item_id = NEW.item_id;
END;

CREATE TRIGGER receipt_sequence_updated_at AFTER UPDATE ON receipt_sequence
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
    UPDATE receipt_sequence SET updated_at = datetime('now', 'localtime') WHERE seq_date = NEW.seq_date;
END;

-- Student change history: one entry per edit of a tracked field.
CREATE TRIGGER log_student_changes AFTER UPDATE ON students
WHEN OLD.student_code IS NOT NEW.student_code OR OLD.first_name IS NOT NEW.first_name
  OR OLD.last_name IS NOT NEW.last_name OR OLD.class IS NOT NEW.class
  OR OLD.parent_phone IS NOT NEW.parent_phone OR OLD.is_active IS NOT NEW.is_active
BEGIN
    INSERT INTO student_audit_log (student_id, action, old_data, new_data)
    VALUES (
        OLD.student_id,
        'UPDATE',
        json_object('student_code', OLD.student_code, 'first_name', OLD.first_name,
                    'last_name', OLD.last_name, 'class', OLD.class,
                    'parent_phone', OLD.parent_phone, 'is_active', OLD.is_active),
        json_object('student_code', NEW.student_code, 'first_name', NEW.first_name,
                    'last_name', NEW.last_name, 'class', NEW.class,
                    'parent_phone', NEW.parent_phone, 'is_active', NEW.is_active)
    );
END;
