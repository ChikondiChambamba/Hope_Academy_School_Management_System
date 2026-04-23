"""
Common SQL queries for the School Management System
"""
from database.connection import db

_HAS_STUDENT_IS_NEW = None

def student_is_new_available() -> bool:
    """Return True if students.is_new column exists in the current DB."""
    global _HAS_STUDENT_IS_NEW
    if _HAS_STUDENT_IS_NEW is None:
        try:
            q = """
                SELECT 1
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'students'
                  AND COLUMN_NAME = 'is_new'
                LIMIT 1
            """
            res = db.execute_query(q, fetch=True)
            _HAS_STUDENT_IS_NEW = bool(res)
        except Exception:
            _HAS_STUDENT_IS_NEW = False
    return _HAS_STUDENT_IS_NEW

def _normalize_is_new(sql: str) -> str:
    """Remove is_new references if the column doesn't exist."""
    if student_is_new_available():
        return sql
    return sql.replace("AND s.is_new = 0", "AND 1=0")

def get_all_students_query() -> str:
    return _normalize_is_new(Queries.GET_ALL_STUDENTS)

def get_student_by_id_query() -> str:
    return _normalize_is_new(Queries.GET_STUDENT_BY_ID)

def search_students_query() -> str:
    return _normalize_is_new(Queries.SEARCH_STUDENTS)

def get_student_fee_details_query() -> str:
    return _normalize_is_new(Queries.GET_STUDENT_FEE_DETAILS)

class Queries:
    """Collection of SQL queries used in the system"""
    
    # Student queries
    GET_ALL_STUDENTS = """
        SELECT s.*,
               COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
               COALESCE(SUM(
                   CASE
                       WHEN sfe.exemption_id IS NOT NULL THEN 0
                       WHEN (LOWER(ft.fee_name) LIKE '%registration%' OR LOWER(ft.fee_name) LIKE '%uniform%') AND s.is_new = 0 THEN 0
                       ELSE ft.amount
                   END
               ), 0) AS total_due,
               COALESCE(SUM(
                   CASE
                       WHEN sfe.exemption_id IS NOT NULL THEN 0
                       WHEN (LOWER(ft.fee_name) LIKE '%registration%' OR LOWER(ft.fee_name) LIKE '%uniform%') AND s.is_new = 0 THEN 0
                       ELSE ft.amount
                   END
               ), 0) - COALESCE(SUM(sf.amount_paid), 0) AS balance
        FROM students s
        LEFT JOIN fee_types ft ON ft.academic_year = %s
        LEFT JOIN student_fee_exemptions sfe ON sfe.student_id = s.student_id AND sfe.fee_type_id = ft.fee_type_id
        LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
        WHERE s.is_active = 1
          AND (
                NOT EXISTS (
                    SELECT 1 FROM fee_type_classes ftc0
                    WHERE ftc0.fee_type_id = ft.fee_type_id
                )
                OR EXISTS (
                    SELECT 1
                    FROM fee_type_classes ftc
                    JOIN classes c ON c.class_id = ftc.class_id
                    WHERE ftc.fee_type_id = ft.fee_type_id
                      AND LOWER(c.class_name) = LOWER(s.class)
                      AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                )
          )
        GROUP BY s.student_id
        ORDER BY s.last_name, s.first_name
    """
    
    GET_STUDENT_BY_ID = """
        SELECT s.*,
               COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
               COALESCE(SUM(
                   CASE
                       WHEN sfe.exemption_id IS NOT NULL THEN 0
                       WHEN (LOWER(ft.fee_name) LIKE '%registration%' OR LOWER(ft.fee_name) LIKE '%uniform%') AND s.is_new = 0 THEN 0
                       ELSE ft.amount
                   END
               ), 0) AS total_due,
               COALESCE(SUM(
                   CASE
                       WHEN sfe.exemption_id IS NOT NULL THEN 0
                       WHEN (LOWER(ft.fee_name) LIKE '%registration%' OR LOWER(ft.fee_name) LIKE '%uniform%') AND s.is_new = 0 THEN 0
                       ELSE ft.amount
                   END
               ), 0) - COALESCE(SUM(sf.amount_paid), 0) AS balance
        FROM students s
        LEFT JOIN fee_types ft ON ft.academic_year = %s
        LEFT JOIN student_fee_exemptions sfe ON sfe.student_id = s.student_id AND sfe.fee_type_id = ft.fee_type_id
        LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
        WHERE s.student_id = %s
          AND (
                NOT EXISTS (
                    SELECT 1 FROM fee_type_classes ftc0
                    WHERE ftc0.fee_type_id = ft.fee_type_id
                )
                OR EXISTS (
                    SELECT 1
                    FROM fee_type_classes ftc
                    JOIN classes c ON c.class_id = ftc.class_id
                    WHERE ftc.fee_type_id = ft.fee_type_id
                      AND LOWER(c.class_name) = LOWER(s.class)
                      AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                )
          )
        GROUP BY s.student_id
    """
    
    SEARCH_STUDENTS = """
        SELECT s.*, 
               COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
               COALESCE(SUM(
                   CASE
                       WHEN sfe.exemption_id IS NOT NULL THEN 0
                       WHEN (LOWER(ft.fee_name) LIKE '%registration%' OR LOWER(ft.fee_name) LIKE '%uniform%') AND s.is_new = 0 THEN 0
                       ELSE ft.amount
                   END
               ), 0) AS total_due,
               COALESCE(SUM(
                   CASE
                       WHEN sfe.exemption_id IS NOT NULL THEN 0
                       WHEN (LOWER(ft.fee_name) LIKE '%registration%' OR LOWER(ft.fee_name) LIKE '%uniform%') AND s.is_new = 0 THEN 0
                       ELSE ft.amount
                   END
               ), 0) - COALESCE(SUM(sf.amount_paid), 0) AS balance
        FROM students s
        LEFT JOIN fee_types ft ON ft.academic_year = %s
        LEFT JOIN student_fee_exemptions sfe ON sfe.student_id = s.student_id AND sfe.fee_type_id = ft.fee_type_id
        LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
        WHERE s.is_active = 1 
          AND (s.first_name LIKE %s OR s.last_name LIKE %s OR s.student_code LIKE %s)
          AND (
                NOT EXISTS (
                    SELECT 1 FROM fee_type_classes ftc0
                    WHERE ftc0.fee_type_id = ft.fee_type_id
                )
                OR EXISTS (
                    SELECT 1
                    FROM fee_type_classes ftc
                    JOIN classes c ON c.class_id = ftc.class_id
                    WHERE ftc.fee_type_id = ft.fee_type_id
                      AND LOWER(c.class_name) = LOWER(s.class)
                      AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                )
          )
        GROUP BY s.student_id
        ORDER BY s.last_name, s.first_name
    """
    
    GET_STUDENT_FEE_DETAILS = """
        SELECT 
            ft.fee_type_id,
            ft.fee_name,
            ft.amount AS expected_amount,
            COALESCE(SUM(sf.amount_paid), 0) AS paid_amount,
            COALESCE(
                CASE
                    WHEN sfe.exemption_id IS NOT NULL THEN 0
                    WHEN (LOWER(ft.fee_name) LIKE '%registration%' OR LOWER(ft.fee_name) LIKE '%uniform%') AND s.is_new = 0 THEN 0
                    ELSE ft.amount
                END, ft.amount
            ) - COALESCE(SUM(sf.amount_paid), 0) AS balance,
            MAX(sf.payment_date) AS last_payment
        FROM fee_types ft
        LEFT JOIN students s ON s.student_id = %s
        LEFT JOIN student_fee_exemptions sfe ON sfe.student_id = s.student_id AND sfe.fee_type_id = ft.fee_type_id
        LEFT JOIN student_fees sf ON ft.fee_type_id = sf.fee_type_id AND sf.student_id = s.student_id
        WHERE ft.academic_year = %s
          AND (
                NOT EXISTS (
                    SELECT 1 FROM fee_type_classes ftc0
                    WHERE ftc0.fee_type_id = ft.fee_type_id
                )
                OR EXISTS (
                    SELECT 1
                    FROM fee_type_classes ftc
                    JOIN classes c ON c.class_id = ftc.class_id
                    WHERE ftc.fee_type_id = ft.fee_type_id
                      AND LOWER(c.class_name) = LOWER(s.class)
                      AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                )
          )
          AND (
                ft.term = %s
                OR ft.term IS NULL
                OR ft.term = ''
                OR NOT EXISTS (
                    SELECT 1
                    FROM fee_types ftx
                    WHERE ftx.academic_year = %s
                      AND ftx.term = %s
                )
          )
        GROUP BY ft.fee_type_id, ft.fee_name, ft.amount
        ORDER BY ft.fee_name
    """
    
    # Teacher queries
    GET_ALL_TEACHERS = """
        SELECT * FROM teachers 
        WHERE is_active = 1 
        ORDER BY last_name, first_name
    """
    
    GET_TEACHER_CLASSES = """
        SELECT c.class_name, c.room_number, COUNT(sc.student_id) AS student_count
        FROM classes c
        LEFT JOIN student_classes sc ON c.class_id = sc.class_id AND sc.academic_year = %s
        WHERE c.teacher_id = %s
        GROUP BY c.class_id, c.class_name, c.room_number
    """
    
    # Fee queries
    GET_FEE_TYPES = """
        SELECT * FROM fee_types 
        WHERE academic_year = %s 
        ORDER BY fee_name
    """
    
    GET_FEE_PAYMENTS_BY_DATE = """
        SELECT 
            sf.*,
            s.first_name,
            s.last_name,
            s.class,
            ft.fee_name
        FROM student_fees sf
        JOIN students s ON sf.student_id = s.student_id
        JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
        WHERE sf.payment_date BETWEEN %s AND %s
        ORDER BY sf.payment_date DESC
    """
    
    GET_TOTAL_FEES_COLLECTED = """
        SELECT 
            YEAR(payment_date) AS year,
            MONTH(payment_date) AS month,
            SUM(amount_paid) AS total_amount,
            COUNT(*) AS payment_count
        FROM student_fees
        WHERE payment_date BETWEEN %s AND %s
        GROUP BY YEAR(payment_date), MONTH(payment_date)
        ORDER BY year DESC, month DESC
    """
    
    # Attendance queries
    GET_ATTENDANCE_BY_DATE = """
        SELECT 
            a.*,
            s.first_name,
            s.last_name,
            s.class
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.attendance_date = %s
        ORDER BY s.class, s.last_name, s.first_name
    """
    
    GET_ATTENDANCE_SUMMARY = """
        SELECT 
            a.attendance_date,
            COUNT(*) AS total_students,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent,
            SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) AS late,
            SUM(CASE WHEN a.status = 'Excused' THEN 1 ELSE 0 END) AS excused
        FROM attendance a
        WHERE a.attendance_date BETWEEN %s AND %s
        GROUP BY a.attendance_date
        ORDER BY a.attendance_date DESC
    """
    
    # Inventory queries
    GET_ALL_INVENTORY = """
        SELECT * FROM inventory_items 
        ORDER BY category, item_name
    """
    
    GET_LOW_STOCK_ITEMS = """
        SELECT * FROM inventory_items 
        WHERE quantity < min_quantity 
        ORDER BY (min_quantity - quantity) DESC
    """
    
    GET_INVENTORY_VALUE = """
        SELECT 
            category,
            COUNT(*) AS item_count,
            SUM(quantity) AS total_quantity,
            SUM(total_value) AS total_value
        FROM inventory_items
        GROUP BY category
        ORDER BY category
    """
    
    # Expense queries
    GET_ALL_EXPENSES = """
        SELECT 
            e.*,
            i.item_name
        FROM expenses e
        LEFT JOIN inventory_items i ON e.item_id = i.item_id
        ORDER BY e.expense_date DESC
    """
    
    GET_EXPENSES_BY_CATEGORY = """
        SELECT 
            category,
            COUNT(*) AS expense_count,
            SUM(amount) AS total_amount
        FROM expenses
        WHERE expense_date BETWEEN %s AND %s
        GROUP BY category
        ORDER BY total_amount DESC
    """
    
    # Dashboard queries
    GET_DASHBOARD_STATS = """
        SELECT 
            (SELECT COUNT(*) FROM students WHERE is_active = 1) AS total_students,
            (SELECT COUNT(*) FROM teachers WHERE is_active = 1) AS total_teachers,
            (SELECT COUNT(DISTINCT class) FROM students WHERE is_active = 1) AS total_classes,
            (SELECT COALESCE(SUM(amount_paid), 0) FROM student_fees 
             WHERE YEAR(payment_date) = YEAR(CURDATE())) AS fees_collected,
            (SELECT COALESCE(SUM(amount), 0) FROM expenses 
             WHERE YEAR(expense_date) = YEAR(CURDATE())) AS expenses_total,
            (SELECT COALESCE(SUM(total_value), 0) FROM inventory_items) AS inventory_value,
            (SELECT COUNT(*) FROM attendance 
             WHERE attendance_date = CURDATE() AND status = 'Present') AS today_present,
            (SELECT COUNT(*) FROM attendance 
             WHERE attendance_date = CURDATE()) AS today_total
    """
    
    GET_RECENT_ACTIVITIES = """
        (SELECT 
            'fee_payment' AS activity_type,
            CONCAT('Fee payment: ', s.first_name, ' ', s.last_name) AS description,
            sf.payment_date AS activity_date,
            sf.amount_paid AS amount
        FROM student_fees sf
        JOIN students s ON sf.student_id = s.student_id
        ORDER BY sf.payment_date DESC
        LIMIT 5)
        
        UNION ALL
        
        (SELECT 
            'expense' AS activity_type,
            CONCAT('Expense: ', description) AS description,
            expense_date AS activity_date,
            amount
        FROM expenses
        ORDER BY expense_date DESC
        LIMIT 5)
        
        ORDER BY activity_date DESC
        LIMIT 10
    """
    
    # Financial summary queries
    GET_FINANCIAL_SUMMARY = """
        SELECT 
            'Revenue' AS category,
            'Fee Collections' AS subcategory,
            COALESCE(SUM(amount_paid), 0) AS amount
        FROM student_fees
        WHERE payment_date BETWEEN %s AND %s
        
        UNION ALL
        
        SELECT 
            'Expense' AS category,
            category AS subcategory,
            COALESCE(SUM(amount), 0) AS amount
        FROM expenses
        WHERE expense_date BETWEEN %s AND %s
        GROUP BY category
        
        UNION ALL
        
        SELECT 
            'Net' AS category,
            'Balance' AS subcategory,
            (SELECT COALESCE(SUM(amount_paid), 0) FROM student_fees 
             WHERE payment_date BETWEEN %s AND %s)
            -
            (SELECT COALESCE(SUM(amount), 0) FROM expenses 
             WHERE expense_date BETWEEN %s AND %s) AS amount
    """
    
    @classmethod
    def get_students_by_class(cls, class_name):
        """Get students in a specific class"""
        return """
            SELECT s.*, 
                   COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
                   COALESCE(SUM(ft.amount), 0) AS total_due,
                   COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) AS balance
            FROM students s
            LEFT JOIN student_fees sf ON s.student_id = sf.student_id
            LEFT JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id AND ft.academic_year = %s
            WHERE s.is_active = 1 AND s.class = %s
            GROUP BY s.student_id
            ORDER BY s.last_name, s.first_name
        """
    
    @classmethod
    def get_student_attendance_history(cls, student_id, start_date, end_date):
        """Get attendance history for a student"""
        return f"""
            SELECT 
                attendance_date,
                status,
                remarks
            FROM attendance
            WHERE student_id = {student_id}
                AND attendance_date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY attendance_date DESC
        """
