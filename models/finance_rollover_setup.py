"""Term rollover schema, templates, and projection helpers."""
from typing import List, Dict, Any
import config
from database.connection import db
from .finance_fee_types import FeeType


class FinanceRolloverSetupMixin:
    @staticmethod
    def _ensure_term_rollover_tables() -> None:
        """Ensure tables used by term rollover logic exist (older MySQL databases)."""
        if db.manages_schema or not db.once('schema.rollover_tables'):
            return
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS term_changes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                academic_year VARCHAR(32) NOT NULL,
                previous_term VARCHAR(32),
                term_name VARCHAR(32) NOT NULL,
                start_date DATE,
                rollover_processed TINYINT(1) DEFAULT 0,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_term_change_year_term (academic_year, term_name)
            ) ENGINE=InnoDB
            """
        )
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS student_term_fee_rollovers (
                rollover_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                from_academic_year VARCHAR(32) NOT NULL,
                from_term VARCHAR(32) NOT NULL,
                to_academic_year VARCHAR(32) NOT NULL,
                to_term VARCHAR(32) NOT NULL,
                carried_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
                source_total_due DECIMAL(12,2) NOT NULL DEFAULT 0,
                source_total_paid DECIMAL(12,2) NOT NULL DEFAULT 0,
                computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_student_to_term (student_id, to_academic_year, to_term),
                INDEX idx_rollover_target (to_academic_year, to_term),
                INDEX idx_rollover_source (from_academic_year, from_term),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        # Backward-compatible migration for older term_changes tables.
        try:
            cols = db.execute_query(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'term_changes'
                """,
                fetch=True
            ) or []
            col_names = {row.get('COLUMN_NAME') for row in cols}

            if 'previous_term' not in col_names:
                db.execute_query("ALTER TABLE term_changes ADD COLUMN previous_term VARCHAR(32) NULL AFTER academic_year")
            if 'rollover_processed' not in col_names:
                db.execute_query("ALTER TABLE term_changes ADD COLUMN rollover_processed TINYINT(1) DEFAULT 0 AFTER start_date")
        except Exception:
            pass

    @staticmethod
    def _ensure_salary_monthly_table() -> None:
        """Ensure monthly salary snapshot table exists (older MySQL databases)."""
        if db.manages_schema or not db.once('schema.salary_monthly'):
            return
        db.execute_query(
            """
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
            ) ENGINE=InnoDB
            """
        )
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS term_rollover_runs (
                run_id INT AUTO_INCREMENT PRIMARY KEY,
                academic_year VARCHAR(32) NOT NULL,
                from_term VARCHAR(32) NOT NULL,
                to_term VARCHAR(32) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'PREVIEW',
                total_students INT NOT NULL DEFAULT 0,
                reset_students INT NOT NULL DEFAULT 0,
                carry_students INT NOT NULL DEFAULT 0,
                previous_outstanding_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                new_term_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                carry_forward_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                opening_balance_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                executed_by VARCHAR(100),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                INDEX idx_rollover_run_lookup (academic_year, from_term, to_term, status)
            ) ENGINE=InnoDB
            """
        )
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS term_rollover_run_items (
                item_id INT AUTO_INCREMENT PRIMARY KEY,
                run_id INT NOT NULL,
                student_id INT NOT NULL,
                student_code VARCHAR(20),
                student_name VARCHAR(150),
                class_name VARCHAR(50),
                previous_outstanding DECIMAL(12,2) NOT NULL DEFAULT 0,
                new_term_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                carry_forward_total DECIMAL(12,2) NOT NULL DEFAULT 0,
                reset_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                opening_balance DECIMAL(12,2) NOT NULL DEFAULT 0,
                payment_status VARCHAR(20) NOT NULL DEFAULT 'Paid',
                carry_status VARCHAR(20) NOT NULL DEFAULT 'Reset',
                details_json LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_rollover_run_student (run_id, student_id),
                INDEX idx_rollover_item_student (student_id),
                FOREIGN KEY (run_id) REFERENCES term_rollover_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        db.execute_query(
            """
            CREATE TABLE IF NOT EXISTS student_term_fee_rollover_items (
                rollover_item_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                from_academic_year VARCHAR(32) NOT NULL,
                from_term VARCHAR(32) NOT NULL,
                to_academic_year VARCHAR(32) NOT NULL,
                to_term VARCHAR(32) NOT NULL,
                source_fee_type_id INT NULL,
                source_fee_name VARCHAR(100) NOT NULL,
                source_is_required TINYINT(1) NOT NULL DEFAULT 1,
                source_is_class_specific TINYINT(1) NOT NULL DEFAULT 0,
                source_expected_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                source_paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                carried_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                source_status VARCHAR(20) NOT NULL DEFAULT 'Paid',
                target_fee_type_id INT NULL,
                target_fee_name VARCHAR(100),
                target_applicable TINYINT(1) NOT NULL DEFAULT 0,
                run_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_rollover_student_source_target (
                    student_id, from_academic_year, from_term, to_academic_year, to_term, source_fee_name
                ),
                INDEX idx_rollover_items_target (to_academic_year, to_term),
                INDEX idx_rollover_items_student (student_id),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        # Backward-compatible migration for older monthly salary tables.
        try:
            cols = db.execute_query(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'teacher_salary_monthly'
                """,
                fetch=True
            ) or []
            col_names = {row.get('COLUMN_NAME') for row in cols}
            if 'is_paid' not in col_names:
                db.execute_query("ALTER TABLE teacher_salary_monthly ADD COLUMN is_paid TINYINT(1) NOT NULL DEFAULT 0 AFTER net_salary")
        except Exception:
            pass

    @staticmethod
    def _get_next_term_name(current_term: str) -> str:
        """Return the next configured term name (wraps after the last term)."""
        terms = list(getattr(config.Config, 'TERMS', ['Term 1', 'Term 2', 'Term 3'])) or ['Term 1', 'Term 2', 'Term 3']
        current_term = config.Config.normalize_term_name(current_term)
        if current_term in terms:
            idx = terms.index(current_term)
            return terms[(idx + 1) % len(terms)]
        return terms[0]

    @staticmethod
    def _resolve_rollover_target(
        from_academic_year: str,
        from_term: str,
        to_term: str = None,
        to_academic_year: str = None,
    ) -> tuple:
        """Return the (academic_year, term) a rollover from `from_term` must land in.

        A rollover always moves to the immediately following period: Term 1 ->
        Term 2 -> Term 3 within a year, and the last term -> Term 1 of the next
        academic year. Skipping a term (losing its fees) or staying in the same
        year after the last term is rejected.
        """
        expected_year, expected_term = config.Config.next_term_period(from_academic_year, from_term)
        if to_term and config.Config.normalize_term_name(to_term) != expected_term:
            raise ValueError(
                f"A rollover from {from_term} ({from_academic_year}) must move to {expected_term} "
                f"({expected_year}), not {to_term}."
            )
        if to_academic_year and to_academic_year.strip() != expected_year:
            raise ValueError(
                f"{expected_term} after {from_term} {from_academic_year} belongs to academic year "
                f"{expected_year}, not {to_academic_year}."
            )
        return expected_year, expected_term

    @staticmethod
    def _ensure_rollover_year_columns() -> None:
        """Older databases lack the columns recording the target/source academic year."""
        if db.manages_schema or not db.once('schema.rollover_year_columns'):
            return
        for table, column, definition in (
            ('term_rollover_runs', 'to_academic_year', 'VARCHAR(32) NULL AFTER to_term'),
            ('term_changes', 'previous_academic_year', 'VARCHAR(32) NULL AFTER academic_year'),
        ):
            if not db.column_exists(table, column):
                db.execute_query(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @classmethod
    def _student_fee_rows_for_term(
        cls,
        academic_year: str,
        term: str,
        treat_new_students_as_continuing: bool = False
    ) -> List[Dict[str, Any]]:
        """Return one row per student/fee type for a specific term."""
        cls._ensure_term_rollover_tables()
        from database.queries import student_is_new_available

        term = config.Config.normalize_term_name(term)
        aliases = config.Config.get_term_aliases(term) or [term]
        placeholders = ", ".join(["%s"] * len(aliases))
        if treat_new_students_as_continuing:
            is_new_guard = "AND 1=1"
        else:
            is_new_guard = "AND s.is_new = 0" if student_is_new_available() else "AND 1=0"
        query = f"""
            SELECT
                s.student_id,
                s.student_code,
                CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                s.class AS class_name,
                ft.fee_type_id,
                ft.fee_name,
                ft.is_required,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM fee_type_classes ftc0
                        WHERE ftc0.fee_type_id = ft.fee_type_id
                    ) THEN 1 ELSE 0
                END AS is_class_specific,
                CASE
                    WHEN sfe.exemption_id IS NOT NULL THEN 0
                    WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') {is_new_guard} THEN 0
                    WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                    WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                    ELSE ft.amount
                END AS expected_amount,
                COALESCE(sf.amount_paid, 0) AS paid_amount
            FROM students s
            JOIN fee_types ft
              ON ft.academic_year = %s
             AND ft.term IN ({placeholders})
            LEFT JOIN student_fee_exemptions sfe
              ON sfe.student_id = s.student_id
             AND sfe.fee_type_id = ft.fee_type_id
            LEFT JOIN (
                SELECT student_id, fee_type_id, COALESCE(SUM(amount_paid), 0) AS amount_paid
                FROM student_fees
                GROUP BY student_id, fee_type_id
            ) sf ON sf.student_id = s.student_id AND sf.fee_type_id = ft.fee_type_id
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
            ORDER BY s.class, s.last_name, s.first_name, ft.fee_name
        """
        return db.execute_query(query, tuple([academic_year] + aliases + [academic_year]), fetch=True) or []

    @staticmethod
    def _get_term_fee_templates(academic_year: str, term: str) -> List[Dict[str, Any]]:
        """Return fee type definitions and class scopes for a term."""
        term = config.Config.normalize_term_name(term)
        aliases = config.Config.get_term_aliases(term) or [term]
        placeholders = ", ".join(["%s"] * len(aliases))
        rows = db.execute_query(
            f"""
            SELECT
                ft.fee_type_id,
                ft.fee_name,
                ft.description,
                ft.amount,
                ft.term,
                ft.academic_year,
                ft.is_required,
                {db.group_concat_distinct("CAST(ftc.class_id AS CHAR)", "','")} AS class_ids,
                {db.group_concat_distinct("LOWER(c.class_name)", "'||'")} AS class_names
            FROM fee_types ft
            LEFT JOIN fee_type_classes ftc
              ON ftc.fee_type_id = ft.fee_type_id
             AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
            LEFT JOIN classes c ON c.class_id = ftc.class_id
            WHERE ft.academic_year = %s
              AND ft.term IN ({placeholders})
            GROUP BY
                ft.fee_type_id, ft.fee_name, ft.description, ft.amount, ft.term, ft.academic_year, ft.is_required
            ORDER BY ft.fee_name, ft.fee_type_id
            """,
            tuple([academic_year, academic_year] + aliases),
            fetch=True
        ) or []

        templates: List[Dict[str, Any]] = []
        for row in rows:
            class_ids = []
            for raw_id in (row.get('class_ids') or '').split(','):
                raw_id = raw_id.strip()
                if raw_id:
                    try:
                        class_ids.append(int(raw_id))
                    except ValueError:
                        pass
            class_names = [name.strip().lower() for name in (row.get('class_names') or '').split('||') if name.strip()]
            templates.append({
                'fee_type_id': row.get('fee_type_id'),
                'fee_name': row.get('fee_name') or '',
                'description': row.get('description') or '',
                'amount': float(row.get('amount') or 0),
                'term': row.get('term') or '',
                'academic_year': row.get('academic_year') or academic_year,
                'is_required': bool(row.get('is_required')),
                'class_ids': class_ids,
                'class_names': class_names
            })
        return templates

    @staticmethod
    def _fee_template_signature(template: Dict[str, Any]) -> tuple:
        """Build a signature that prevents duplicate fee cloning."""
        scope = tuple(sorted((template.get('class_names') or [])))
        return (
            (template.get('fee_name') or '').strip().lower(),
            bool(template.get('is_required')),
            scope
        )

    @classmethod
    def _build_projected_term_fee_rows(
        cls,
        from_academic_year: str,
        from_term: str,
        to_academic_year: str,
        to_term: str,
        treat_new_students_as_continuing: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """Project next-term student fee rows, inheriting missing fee types from the previous term."""
        from database.queries import student_is_new_available

        target_templates = cls._get_term_fee_templates(to_academic_year, to_term)
        source_templates = cls._get_term_fee_templates(from_academic_year, from_term)
        existing_signatures = {cls._fee_template_signature(t) for t in target_templates}

        effective_templates = list(target_templates)
        inherited_templates = 0
        for template in source_templates:
            signature = cls._fee_template_signature(template)
            if signature in existing_signatures:
                continue
            inherited_templates += 1
            effective_templates.append({
                **template,
                'fee_type_id': None,
                'term': to_term,
                'academic_year': to_academic_year
            })
            existing_signatures.add(signature)

        if not effective_templates:
            return [], 0

        student_rows = db.execute_query(
            """
            SELECT
                student_id,
                student_code,
                CONCAT(first_name, ' ', last_name) AS student_name,
                class
                {is_new_column}
            FROM students
            WHERE is_active = 1
            ORDER BY class, last_name, first_name
            """.format(is_new_column=", is_new" if student_is_new_available() else ""),
            fetch=True
        ) or []

        projected_rows: List[Dict[str, Any]] = []
        for student in student_rows:
            student_class = (student.get('class') or '').strip().lower()
            is_new_student = False if treat_new_students_as_continuing else (bool(student.get('is_new')) if student_is_new_available() else False)
            for template in effective_templates:
                class_scope = template.get('class_names') or []
                if class_scope and student_class not in class_scope:
                    continue

                fee_name = template.get('fee_name') or ''
                expected_amount = float(template.get('amount') or 0)
                lower_fee_name = fee_name.lower()
                if ('registration' in lower_fee_name or 'uniform' in lower_fee_name) and not is_new_student:
                    expected_amount = 0.0
                elif 'tuition' in lower_fee_name and ('nursery' in student_class or 'reception' in student_class):
                    expected_amount = 45000.0
                elif 'tuition' in lower_fee_name:
                    expected_amount = 85000.0

                projected_rows.append({
                    'student_id': student.get('student_id'),
                    'student_code': student.get('student_code') or '',
                    'student_name': student.get('student_name') or '',
                    'class_name': student.get('class') or '',
                    'fee_type_id': template.get('fee_type_id'),
                    'fee_name': fee_name,
                    'is_required': 1 if template.get('is_required') else 0,
                    'is_class_specific': 1 if class_scope else 0,
                    'expected_amount': expected_amount,
                    'paid_amount': 0.0
                })
        return projected_rows, inherited_templates

    @classmethod
    def _clone_missing_fee_types_to_term(
        cls,
        connection,
        from_academic_year: str,
        from_term: str,
        to_academic_year: str,
        to_term: str,
    ) -> int:
        """Copy missing fee types and class mappings into the target term inside a transaction.

        Across a year boundary the copies belong to the new academic year.
        """
        source_templates = cls._get_term_fee_templates(from_academic_year, from_term)
        target_templates = cls._get_term_fee_templates(to_academic_year, to_term)
        existing_signatures = {cls._fee_template_signature(t) for t in target_templates}
        cloned = 0

        for template in source_templates:
            signature = cls._fee_template_signature(template)
            if signature in existing_signatures:
                continue

            new_fee_type_id = db.execute_query_in_transaction(
                connection,
                """
                INSERT INTO fee_types (fee_name, description, amount, term, academic_year, is_required)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    template.get('fee_name') or '',
                    template.get('description') or '',
                    float(template.get('amount') or 0),
                    to_term,
                    to_academic_year,
                    1 if template.get('is_required') else 0
                )
            )

            for class_id in template.get('class_ids') or []:
                db.execute_query_in_transaction(
                    connection,
                    """
                    INSERT IGNORE INTO fee_type_classes (fee_type_id, class_id, academic_year)
                    VALUES (%s, %s, %s)
                    """,
                    (new_fee_type_id, class_id, to_academic_year)
                )

            existing_signatures.add(signature)
            cloned += 1

        return cloned


