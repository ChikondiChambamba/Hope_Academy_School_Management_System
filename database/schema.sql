-- School Management System Database Schema
-- Version: 1.0.0

--
-- Run with:  python setup_database.py
-- (creates the database named in config / HOPE_DB_NAME and executes this file).
-- This script is NON-destructive: it never drops data. To wipe and rebuild a
-- database deliberately, use scripts/reset_database.py, which backs up first.
--
-- Stored routines and triggers use DELIMITER blocks, so the file also runs
-- unchanged in the mysql command-line client.

-- Students Table
CREATE TABLE students (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    student_code VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    class VARCHAR(20) NOT NULL,
    birth_date DATE,
    parent_name VARCHAR(100),
    parent_phone VARCHAR(20),
    parent_email VARCHAR(100),
    address TEXT,
    enrollment_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_new BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_student_code (student_code),
    INDEX idx_class (class),
    INDEX idx_last_name (last_name),
    INDEX idx_active (is_active)
);

-- Teachers Table
CREATE TABLE teachers (
    teacher_id INT PRIMARY KEY AUTO_INCREMENT,
    teacher_code VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    subject_specialization VARCHAR(100),
    hire_date DATE NOT NULL,
    salary_amount DECIMAL(10,2) DEFAULT 0.00,
    allowance_amount DECIMAL(10,2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_teacher_code (teacher_code),
    INDEX idx_last_name (last_name),
    INDEX idx_active (is_active)
);

-- Fee Types Table
CREATE TABLE fee_types (
    fee_type_id INT PRIMARY KEY AUTO_INCREMENT,
    fee_name VARCHAR(100) NOT NULL,
    description TEXT,
    amount DECIMAL(10,2) NOT NULL,
    term VARCHAR(20),
    academic_year VARCHAR(20) NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_academic_year (academic_year),
    INDEX idx_term (term),
    INDEX idx_fee_types_year_term (academic_year, term)
);

-- Student Fees Table
CREATE TABLE student_fees (
    fee_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    fee_type_id INT NOT NULL,
    amount_paid DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_method ENUM('Cash', 'Mobile money', 'M-Pesa', 'Bank Transfer', 'Check', 'Other') DEFAULT 'Cash',
    receipt_number VARCHAR(50) UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (fee_type_id) REFERENCES fee_types(fee_type_id) ON DELETE CASCADE,
    
    INDEX idx_student_id (student_id),
    INDEX idx_student_fee_type (student_id, fee_type_id),
    INDEX idx_fee_type_id (fee_type_id),
    INDEX idx_payment_date (payment_date),
    INDEX idx_receipt (receipt_number)
);

-- Receipt Sequence Table: provides an atomic per-day sequence for receipt numbers
CREATE TABLE receipt_sequence (
    seq_date VARCHAR(8) PRIMARY KEY,
    seq INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Student Fee Exemptions: store fee types waived for a student (e.g., other tuition when one paid)
CREATE TABLE student_fee_exemptions (
    exemption_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    fee_type_id INT NOT NULL,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (fee_type_id) REFERENCES fee_types(fee_type_id) ON DELETE CASCADE,

    UNIQUE KEY unique_student_fee_exemption (student_id, fee_type_id),
    INDEX idx_student_exemptions (student_id)
);

-- Term changes history table
CREATE TABLE term_changes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    academic_year VARCHAR(32) NOT NULL,            -- year of the term that was opened
    previous_academic_year VARCHAR(32),            -- year of the term that was closed
    previous_term VARCHAR(32),
    term_name VARCHAR(32) NOT NULL,
    start_date DATE,
    rollover_processed BOOLEAN DEFAULT FALSE,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_term_change_year_term (academic_year, term_name)
);

-- Stores opening balance carried into a new term per student
CREATE TABLE student_term_fee_rollovers (
    rollover_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    from_academic_year VARCHAR(32) NOT NULL,
    from_term VARCHAR(32) NOT NULL,
    to_academic_year VARCHAR(32) NOT NULL,
    to_term VARCHAR(32) NOT NULL,
    carried_balance DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    source_total_due DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    source_total_paid DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_student_to_term (student_id, to_academic_year, to_term),
    INDEX idx_rollover_target (to_academic_year, to_term),
    INDEX idx_rollover_source (from_academic_year, from_term),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE term_rollover_runs (
    run_id INT PRIMARY KEY AUTO_INCREMENT,
    academic_year VARCHAR(32) NOT NULL,            -- year of from_term
    from_term VARCHAR(32) NOT NULL,
    to_term VARCHAR(32) NOT NULL,
    to_academic_year VARCHAR(32),                  -- year of to_term (next year after the last term)
    status VARCHAR(20) NOT NULL DEFAULT 'PREVIEW',
    total_students INT NOT NULL DEFAULT 0,
    reset_students INT NOT NULL DEFAULT 0,
    carry_students INT NOT NULL DEFAULT 0,
    previous_outstanding_total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    new_term_total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    carry_forward_total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    opening_balance_total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    executed_by VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_rollover_run_lookup (academic_year, from_term, to_term, status)
);

CREATE TABLE term_rollover_run_items (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    run_id INT NOT NULL,
    student_id INT NOT NULL,
    student_code VARCHAR(20),
    student_name VARCHAR(150),
    class_name VARCHAR(50),
    previous_outstanding DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    new_term_total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    carry_forward_total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    reset_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    opening_balance DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'Paid',
    carry_status VARCHAR(20) NOT NULL DEFAULT 'Reset',
    details_json LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_rollover_run_student (run_id, student_id),
    INDEX idx_rollover_item_student (student_id),
    FOREIGN KEY (run_id) REFERENCES term_rollover_runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

CREATE TABLE student_term_fee_rollover_items (
    rollover_item_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    from_academic_year VARCHAR(32) NOT NULL,
    from_term VARCHAR(32) NOT NULL,
    to_academic_year VARCHAR(32) NOT NULL,
    to_term VARCHAR(32) NOT NULL,
    source_fee_type_id INT NULL,
    source_fee_name VARCHAR(100) NOT NULL,
    source_is_required BOOLEAN DEFAULT TRUE,
    source_is_class_specific BOOLEAN DEFAULT FALSE,
    source_expected_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    source_paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    carried_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    source_status VARCHAR(20) NOT NULL DEFAULT 'Paid',
    target_fee_type_id INT NULL,
    target_fee_name VARCHAR(100),
    target_applicable BOOLEAN DEFAULT FALSE,
    run_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_rollover_student_source_target (
        student_id, from_academic_year, from_term, to_academic_year, to_term, source_fee_name
    ),
    INDEX idx_rollover_items_target (to_academic_year, to_term),
    INDEX idx_rollover_items_student (student_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- Teacher Salary Advances: track advances given to teachers
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
);

-- Inventory Items Table
CREATE TABLE inventory_items (
    item_id INT PRIMARY KEY AUTO_INCREMENT,
    item_code VARCHAR(50) UNIQUE NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    quantity INT DEFAULT 0,
    unit_price DECIMAL(10,2),
    total_value DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    min_quantity INT DEFAULT 10,
    max_quantity INT DEFAULT 100,
    location VARCHAR(100),
    supplier VARCHAR(100),
    last_restocked DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_category (category),
    INDEX idx_item_code (item_code),
    INDEX idx_low_stock (quantity)
);

-- Expenses Table
CREATE TABLE expenses (
    expense_id INT PRIMARY KEY AUTO_INCREMENT,
    expense_date DATE NOT NULL,
    item_id INT,
    description VARCHAR(200) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    academic_year VARCHAR(32),
    term VARCHAR(32),
    payment_method ENUM('Cash', 'Mobile money', 'M-Pesa', 'Bank Transfer', 'Check', 'Other') DEFAULT 'Cash',
    receipt_number VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (item_id) REFERENCES inventory_items(item_id) ON DELETE SET NULL,
    
    INDEX idx_expense_date (expense_date),
    INDEX idx_expenses_year_term (academic_year, term),
    INDEX idx_category (category),
    INDEX idx_receipt (receipt_number)
);

-- Attendance Table
CREATE TABLE attendance (
    attendance_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status ENUM('Present', 'Absent', 'Late', 'Excused') DEFAULT 'Present',
    check_in_time TIME,
    check_out_time TIME,
    remarks TEXT,
    recorded_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE KEY unique_attendance (student_id, attendance_date),
    
    INDEX idx_attendance_date (attendance_date),
    INDEX idx_status (status),
    INDEX idx_student_date (student_id, attendance_date)
);

-- Classes Table
CREATE TABLE classes (
    class_id INT PRIMARY KEY AUTO_INCREMENT,
    class_name VARCHAR(20) UNIQUE NOT NULL,
    teacher_id INT,
    room_number VARCHAR(20),
    academic_year VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL,
    
    INDEX idx_class_name (class_name),
    INDEX idx_academic_year (academic_year)
);

-- Student-Class Relationship
CREATE TABLE student_classes (
    student_class_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    class_id INT NOT NULL,
    academic_year VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE,
    UNIQUE KEY unique_student_class_year (student_id, class_id, academic_year),
    
    INDEX idx_student_id (student_id),
    INDEX idx_class_id (class_id)
);

-- Mapping table for fee types to classes (allow fee types to target specific classes)
CREATE TABLE fee_type_classes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    fee_type_id INT NOT NULL,
    class_id INT NOT NULL,
    academic_year VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (fee_type_id) REFERENCES fee_types(fee_type_id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(class_id) ON DELETE CASCADE,

    UNIQUE KEY unique_fee_type_class (fee_type_id, class_id)
);

-- Create Views for Common Queries

-- View for Daily Attendance Summary
CREATE VIEW daily_attendance_summary AS
SELECT 
    attendance_date,
    COUNT(*) AS total_students,
    SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
    SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
    SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) AS late_count,
    SUM(CASE WHEN status = 'Excused' THEN 1 ELSE 0 END) AS excused_count,
    ROUND((SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) AS attendance_rate
FROM attendance
GROUP BY attendance_date
ORDER BY attendance_date DESC;

-- View for Inventory Low Stock
CREATE VIEW low_stock_items AS
SELECT 
    item_id,
    item_code,
    item_name,
    category,
    quantity,
    min_quantity,
    unit_price,
    total_value,
    (min_quantity - quantity) AS reorder_quantity
FROM inventory_items
WHERE quantity < min_quantity
ORDER BY (min_quantity - quantity) DESC;

-- View for Financial Summary
CREATE VIEW financial_summary AS
SELECT 
    YEAR(payment_date) AS year,
    MONTH(payment_date) AS month,
    'Revenue' AS type,
    SUM(amount_paid) AS amount
FROM student_fees
GROUP BY YEAR(payment_date), MONTH(payment_date)
UNION ALL
SELECT 
    YEAR(expense_date) AS year,
    MONTH(expense_date) AS month,
    'Expense' AS type,
    SUM(amount) AS amount
FROM expenses
GROUP BY YEAR(expense_date), MONTH(expense_date)
ORDER BY year DESC, month DESC;

-- Create Stored Procedures

-- Procedure to get monthly financial report
DELIMITER $$
CREATE PROCEDURE GetMonthlyFinancialReport(IN year INT, IN month INT)
BEGIN
    -- Revenue
    SELECT 
        'Revenue' AS category,
        'Fee Payments' AS description,
        SUM(amount_paid) AS amount
    FROM student_fees
    WHERE YEAR(payment_date) = year AND MONTH(payment_date) = month;

    -- Expenses
    SELECT 
        'Expense' AS category,
        category AS description,
        SUM(amount) AS amount
    FROM expenses
    WHERE YEAR(expense_date) = year AND MONTH(expense_date) = month
    GROUP BY category;

    -- Net
    SELECT 
        'Net' AS category,
        'Balance' AS description,
        (SELECT COALESCE(SUM(amount_paid), 0) FROM student_fees 
         WHERE YEAR(payment_date) = year AND MONTH(payment_date) = month)
        -
        (SELECT COALESCE(SUM(amount), 0) FROM expenses 
         WHERE YEAR(expense_date) = year AND MONTH(expense_date) = month) AS amount;
END$$
DELIMITER ;

-- Create Triggers

-- inventory_items.total_value is a STORED generated column; it needs no trigger.

-- Trigger to prevent duplicate receipt numbers
DELIMITER $$
CREATE TRIGGER prevent_duplicate_receipt
BEFORE INSERT ON student_fees
FOR EACH ROW
BEGIN
    IF NEW.receipt_number IS NOT NULL THEN
        IF EXISTS (SELECT 1 FROM student_fees WHERE receipt_number = NEW.receipt_number) THEN
            SIGNAL SQLSTATE '45000' 
            SET MESSAGE_TEXT = 'Receipt number already exists';
        END IF;
    END IF;
END$$
DELIMITER ;

-- Trigger to log student updates
CREATE TABLE student_audit_log (
    audit_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    action VARCHAR(20),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100),
    old_data JSON,
    new_data JSON
);

DELIMITER $$
CREATE TRIGGER log_student_changes
AFTER UPDATE ON students
FOR EACH ROW
BEGIN
    INSERT INTO student_audit_log (student_id, action, old_data, new_data)
    VALUES (
        OLD.student_id,
        'UPDATE',
        JSON_OBJECT(
            'student_code', OLD.student_code,
            'first_name', OLD.first_name,
            'last_name', OLD.last_name,
            'class', OLD.class,
            'parent_phone', OLD.parent_phone,
            'is_active', OLD.is_active
        ),
        JSON_OBJECT(
            'student_code', NEW.student_code,
            'first_name', NEW.first_name,
            'last_name', NEW.last_name,
            'class', NEW.class,
            'parent_phone', NEW.parent_phone,
            'is_active', NEW.is_active
        )
    );
END$$
DELIMITER ;

-- Expense categories (also ensured at runtime by models/expense_category.py)
CREATE TABLE IF NOT EXISTS expense_categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Monthly payroll snapshots (also ensured at runtime by FinancialManager)
CREATE TABLE IF NOT EXISTS teacher_salary_monthly (
    payroll_id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id INT NOT NULL,
    payroll_month VARCHAR(7) NOT NULL,
    base_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
    allowance_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    advances_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    gross_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
    net_salary DECIMAL(12,2) NOT NULL DEFAULT 0,
    is_paid TINYINT(1) NOT NULL DEFAULT 0,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_teacher_month (teacher_id, payroll_month),
    INDEX idx_salary_month (payroll_month),
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Audit Log Table
CREATE TABLE audit_log (
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
);

COMMIT;
