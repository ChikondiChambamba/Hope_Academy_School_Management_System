-- School Management System Database Schema
-- Version: 1.0.0

DROP DATABASE IF EXISTS school_management;
CREATE DATABASE IF NOT EXISTS school_management;
USE school_management;

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
    INDEX idx_term (term)
);

-- Student Fees Table
CREATE TABLE student_fees (
    fee_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    fee_type_id INT NOT NULL,
    amount_paid DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    payment_method ENUM('Cash', 'M-Pesa', 'Bank Transfer', 'Check', 'Other') DEFAULT 'Cash',
    receipt_number VARCHAR(50) UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (fee_type_id) REFERENCES fee_types(fee_type_id) ON DELETE CASCADE,
    
    INDEX idx_student_id (student_id),
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
    payment_method ENUM('Cash', 'M-Pesa', 'Bank Transfer', 'Check', 'Other') DEFAULT 'Cash',
    receipt_number VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (item_id) REFERENCES inventory_items(item_id) ON DELETE SET NULL,
    
    INDEX idx_expense_date (expense_date),
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

-- View for Student Fee Summary
CREATE VIEW student_fee_summary AS
SELECT 
    s.student_id,
    s.student_code,
    CONCAT(s.first_name, ' ', s.last_name) AS student_name,
    s.class,
    ft.academic_year,
    SUM(ft.amount) AS total_fees_due,
    COALESCE(SUM(sf.amount_paid), 0) AS total_fees_paid,
    SUM(ft.amount) - COALESCE(SUM(sf.amount_paid), 0) AS balance
FROM students s
CROSS JOIN fee_types ft
LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
WHERE s.is_active = 1 AND ft.academic_year = '2024'
GROUP BY s.student_id, s.student_code, s.first_name, s.last_name, s.class, ft.academic_year;

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

-- Procedure to calculate student balance
CREATE PROCEDURE CalculateStudentBalance(IN student_id INT)
BEGIN
    SELECT 
        s.student_id,
        CONCAT(s.first_name, ' ', s.last_name) AS student_name,
        s.class,
        ft.academic_year,
        SUM(ft.amount) AS total_fees_due,
        COALESCE(SUM(sf.amount_paid), 0) AS total_fees_paid,
        SUM(ft.amount) - COALESCE(SUM(sf.amount_paid), 0) AS balance
    FROM students s
    CROSS JOIN fee_types ft
    LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
    WHERE s.student_id = student_id AND ft.academic_year = '2024'
    GROUP BY s.student_id, s.first_name, s.last_name, s.class, ft.academic_year;
END;

-- Procedure to get monthly financial report
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
END;

-- Create Triggers

-- Trigger to update inventory total value
CREATE TRIGGER update_inventory_value
BEFORE UPDATE ON inventory_items
FOR EACH ROW
BEGIN
    SET NEW.total_value = NEW.quantity * NEW.unit_price;
END;

-- Trigger to prevent duplicate receipt numbers
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
END;

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
END;

-- Insert Sample Data (Optional - remove in production)
INSERT INTO students (student_code, first_name, last_name, class, birth_date, parent_name, parent_phone, address, enrollment_date) VALUES

INSERT INTO teachers (teacher_code, first_name, last_name, phone, email, subject_specialization, hire_date) VALUES


INSERT INTO inventory_items (item_code, item_name, category, quantity, unit_price, min_quantity, supplier) VALUES


INSERT INTO student_fees (student_id, fee_type_id, amount_paid, payment_date, payment_method, receipt_number) VALUES


INSERT INTO expenses (expense_date, description, amount, category, payment_method, receipt_number) VALUES

INSERT INTO attendance (student_id, attendance_date, status, remarks) VALUES

-- Update classes with teachers
UPDATE classes SET teacher_id = 1 WHERE class_name = 'Grade 1';
UPDATE classes SET teacher_id = 2 WHERE class_name = 'Grade 2';
UPDATE classes SET teacher_id = 3 WHERE class_name = 'Grade 3';
UPDATE classes SET teacher_id = 4 WHERE class_name = 'Grade 4';

-- Assign students to classes
INSERT INTO student_classes (student_id, class_id, academic_year) VALUES
(1, 1, '2026'),
(2, 1, '2026'),
(3, 4, '2026'),
(4, 5, '2026'),
(5, 8, '2026');

-- Sample data removed for a clean production-like schema. To re-add
-- the sample data, run a separate provisioning script or execute the
-- original INSERT statements from a safe, reviewed file.
COMMIT;