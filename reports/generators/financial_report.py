"""
Financial report generators
"""
import os
from datetime import datetime, date
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
import config
from database.connection import db
from utils.helpers import format_currency, parse_currency

def generate_fee_collection_report(filename, start_date=None, end_date=None):
    """Generate fee collection report"""
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get data
    query = """
        SELECT 
            sf.payment_date,
            s.student_code,
            CONCAT(s.first_name, ' ', s.last_name) as student_name,
            s.class,
            ft.fee_name,
            sf.amount_paid,
            sf.payment_method,
            sf.receipt_number
        FROM student_fees sf
        JOIN students s ON sf.student_id = s.student_id
        JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
        WHERE sf.payment_date BETWEEN %s AND %s
        ORDER BY sf.payment_date DESC
    """
    
    data = db.execute_query(query, (start_date, end_date), fetch=True)
    
    # Calculate total
    total_amount = sum(row['amount_paid'] for row in data) if data else 0
    
    # Create story
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    story.append(Paragraph(f"FEE COLLECTION REPORT", title_style))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Total Records:', len(data)],
        ['Total Amount:', format_currency(total_amount)],
        ['Start Date:', start_date],
        ['End Date:', end_date]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Main data table
    if data:
        # Prepare table data
        table_data = [['Date', 'Student Code', 'Name', 'Class', 'Fee Type', 'Amount', 'Method', 'Receipt']]
        
        for row in data:
                table_data.append([
                row['payment_date'].strftime('%Y-%m-%d') if row['payment_date'] else '',
                row['student_code'],
                row['student_name'],
                row['class'],
                row['fee_name'],
                    format_currency(float(row['amount_paid'])),
                row['payment_method'],
                row['receipt_number'] or ''
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.7*inch, 0.8*inch, 1.2*inch, 0.6*inch, 1*inch, 0.7*inch, 0.7*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        # Alternate row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.lightgrey)]))
        
        story.append(table)
    else:
        story.append(Paragraph("No data found for the selected period.", styles['Normal']))
    
    # Build PDF
    doc.build(story)

def generate_expense_report(filename, start_date=None, end_date=None, academic_year=None, term=None):
    """Generate expense report"""
    academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
    term = term or None
    term_mode = bool(term and not start_date and not end_date)

    if term_mode:
        start_date, end_date = config.Config.get_term_date_bounds(term)

    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get data
    if term_mode:
        from models.finance import Expense

        data = [
            {
                'expense_date': expense.expense_date,
                'description': expense.description,
                'category': expense.category,
                'amount': expense.amount,
                'payment_method': expense.payment_method,
                'receipt_number': expense.receipt_number,
                'item_name': expense.item_name,
            }
            for expense in Expense.get_term_expenses(academic_year, term)
        ]
    else:
        query = """
            SELECT
                e.expense_date,
                e.description,
                e.category,
                e.amount,
                e.payment_method,
                e.receipt_number,
                i.item_name
            FROM expenses e
            LEFT JOIN inventory_items i ON e.item_id = i.item_id
            WHERE e.expense_date BETWEEN %s AND %s
            ORDER BY e.expense_date DESC
        """

        data = db.execute_query(query, (start_date, end_date), fetch=True)
    
    # Calculate totals
    total_amount = sum(row['amount'] for row in data) if data else 0
    
    # Create story
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1
    )
    
    story.append(Paragraph(f"EXPENSE REPORT", title_style))
    if term_mode:
        story.append(Paragraph(f"Academic Year: {academic_year} - {term}", styles['Normal']))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Total Records:', len(data)],
        ['Total Amount:', format_currency(total_amount)],
        ['Start Date:', start_date],
        ['End Date:', end_date]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Main data table
    if data:
        # Prepare table data
        table_data = [['Date', 'Description', 'Category', 'Amount', 'Method', 'Receipt', 'Item']]
        
        for row in data:
            table_data.append([
                row['expense_date'].strftime('%Y-%m-%d') if row['expense_date'] else '',
                row['description'],
                row['category'],
                format_currency(float(row['amount'])),
                row['payment_method'],
                row['receipt_number'] or '',
                row['item_name'] or ''
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.7*inch, 2*inch, 1*inch, 0.8*inch, 0.7*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        # Alternate row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.lightgrey)]))
        
        story.append(table)
    else:
        story.append(Paragraph("No data found for the selected period.", styles['Normal']))
    
    # Build PDF
    doc.build(story)

def generate_financial_summary_report(filename, academic_year=None, term=None):
    """Generate financial summary report"""
    if not academic_year:
        academic_year = config.Config.CURRENT_ACADEMIC_YEAR
    if not term:
        term = config.Config.CURRENT_TERM
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    from models.finance import FinancialManager

    summary = FinancialManager.get_term_financial_summary(academic_year=academic_year, term=term)
    fee_data = summary.get('monthly_breakdown') or []
    expense_data = summary.get('expense_categories') or []
    total_fees = float(summary.get('total_income') or 0)
    total_expenses = float(summary.get('total_expenses') or 0)
    net_balance = float(summary.get('net_balance') or 0)
    
    # Create story
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1
    )
    
    story.append(Paragraph(f"FINANCIAL SUMMARY REPORT", title_style))
    story.append(Paragraph(f"Academic Year: {academic_year} - {term}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Overall summary
    summary_data = [
        ['Total Fee Collections:', format_currency(total_fees)],
        ['Total Expenses:', format_currency(total_expenses)],
        ['Net Balance:', format_currency(net_balance)],
        ['', ''],
        ['Fee Collections (Monthly):', ''],
        ['', '']
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('SPAN', (0, 4), (1, 4)),
        ('BACKGROUND', (0, 4), (1, 4), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (1, 3), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Monthly fee breakdown
    if fee_data:
        fee_table_data = [['Month', 'Total Fees', 'Payment Count']]
        
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        for row in fee_data:
            month_name = row.get('month') or ''
            fee_table_data.append([
                month_name,
                format_currency(float(row.get('income') or 0)),
                row.get('payment_count', '')
            ])
        
        fee_table = Table(fee_table_data, colWidths=[1*inch, 1.5*inch, 1*inch])
        fee_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("Monthly Fee Collections", styles['Heading2']))
        story.append(fee_table)
        story.append(Spacer(1, 20))
    
    # Expense breakdown
    if expense_data:
        expense_table_data = [['Category', 'Total Amount', 'Expense Count']]
        
        for row in expense_data:
            expense_table_data.append([
                row['category'],
                format_currency(float(row['total_amount'])),
                row['expense_count']
            ])
        
        expense_table = Table(expense_table_data, colWidths=[2*inch, 1.5*inch, 1*inch])
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(Paragraph("Expense Breakdown by Category", styles['Heading2']))
        story.append(expense_table)
    
    # Build PDF
    doc.build(story)

def generate_salary_report(filename, year_month=None):
    """Generate salary report"""
    if not year_month:
        year_month = date.today().strftime('%Y-%m')
    try:
        start_date = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
    except Exception:
        start_date = date.today().replace(day=1)
        year_month = start_date.strftime('%Y-%m')
    if start_date.month == 12:
        end_exclusive = date(start_date.year + 1, 1, 1)
    else:
        end_exclusive = date(start_date.year, start_date.month + 1, 1)

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    query = """
        SELECT
            t.teacher_code,
            CONCAT(t.first_name, ' ', t.last_name) AS teacher_name,
            COALESCE(t.salary_amount, 0) AS base_salary,
            COALESCE(t.allowance_amount, 0) AS allowance,
            COALESCE(SUM(CASE
                WHEN tsa.status IN ('Approved', 'Deducted')
                 AND tsa.advance_date >= %s
                 AND tsa.advance_date < %s
                THEN tsa.advance_amount
                ELSE 0
            END), 0) AS total_advances
        FROM teachers t
        LEFT JOIN teacher_salary_advances tsa ON tsa.teacher_id = t.teacher_id
        WHERE t.is_active = 1
        GROUP BY t.teacher_id, t.teacher_code, t.first_name, t.last_name, t.salary_amount, t.allowance_amount
        ORDER BY t.last_name, t.first_name
    """
    data = db.execute_query(query, (start_date, end_exclusive), fetch=True) or []

    total_salary_only = 0.0
    total_salary_with_allowance = 0.0
    total_advances = 0.0
    total_net_salary = 0.0

    for row in data:
        salary = float(row.get('base_salary') or 0)
        allowance = float(row.get('allowance') or 0)
        advances = float(row.get('total_advances') or 0)
        total_salary_only += salary
        total_salary_with_allowance += salary + allowance
        total_advances += advances
        total_net_salary += (salary + allowance - advances)

    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1
    )

    story.append(Paragraph("SALARY REPORT", title_style))
    story.append(Paragraph(f"Payroll Month: {year_month}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))

    summary_data = [
        ['Total Active Staff:', len(data)],
        ['Salaries Only:', format_currency(total_salary_only)],
        ['Salaries + Allowances:', format_currency(total_salary_with_allowance)],
        ['Total Advances (Approved/Deducted):', format_currency(total_advances)],
        ['Net Salary Payable:', format_currency(total_net_salary)]
    ]
    summary_table = Table(summary_data, colWidths=[3.0*inch, 2.0*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    if data:
        table_data = [['Code', 'Teacher', 'Base Salary', 'Allowance', 'Advances', 'Net Salary']]
        for row in data:
            salary = float(row.get('base_salary') or 0)
            allowance = float(row.get('allowance') or 0)
            advances = float(row.get('total_advances') or 0)
            net_salary = (salary + allowance) - advances
            table_data.append([
                row.get('teacher_code') or '',
                row.get('teacher_name') or '',
                format_currency(salary),
                format_currency(allowance),
                format_currency(advances),
                format_currency(net_salary)
            ])

        table = Table(table_data, colWidths=[0.8*inch, 1.8*inch, 1.0*inch, 0.9*inch, 0.9*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.lightgrey)]))
        story.append(table)
    else:
        story.append(Paragraph("No active teachers found.", styles['Normal']))

    doc.build(story)

def _resolve_fee_type_ids(academic_year, fee_type_filter):
    """Resolve fee filter string to ids; None means all fee types."""
    selected = (fee_type_filter or 'All Fee Types').strip()
    if selected == 'All Fee Types':
        return None
    if selected == 'Tuition Fees Only':
        rows = db.execute_query(
            """
            SELECT fee_type_id
            FROM fee_types
            WHERE academic_year = %s AND LOWER(fee_name) LIKE '%%tuition%%'
            ORDER BY fee_type_id
            """,
            (academic_year,),
            fetch=True
        ) or []
        return [int(r['fee_type_id']) for r in rows if r.get('fee_type_id') is not None]

    try:
        import re
        m = re.search(r'\(#(\d+)\)\s*$', selected)
        if m:
            return [int(m.group(1))]
    except Exception:
        pass
    return None

def build_student_fees_report_data(academic_year=None, class_filter="All", balance_filter="All", fee_type_filter="All Fee Types", term=None):
    """Build student-fee report rows with carried-forward and current-fee breakdowns."""
    if not academic_year:
        academic_year = config.Config.CURRENT_ACADEMIC_YEAR
    if not term:
        term = config.Config.CURRENT_TERM

    from models.finance import FinancialManager
    fee_type_ids = _resolve_fee_type_ids(academic_year, fee_type_filter)
    if fee_type_ids is None:
        balances = FinancialManager.get_student_balances(
            academic_year=academic_year,
            term=term
        )
    elif len(fee_type_ids) == 1:
        balances = FinancialManager.get_student_balances(
            academic_year=academic_year,
            fee_type_id=fee_type_ids[0],
            term=term
        )
    elif len(fee_type_ids) > 1:
        merged = {}
        for fid in fee_type_ids:
            rows = FinancialManager.get_student_balances(
                academic_year=academic_year,
                fee_type_id=fid,
                term=term
            ) or []
            for row in rows:
                sid = row.get('student_id')
                if sid is None:
                    continue
                if sid not in merged:
                    merged[sid] = {
                        'student_id': sid,
                        'student_code': row.get('student_code'),
                        'student_name': row.get('student_name'),
                        'class': row.get('class'),
                        'total_due': 0.0,
                        'total_paid': 0.0,
                        'current_paid': 0.0,
                        'carried_balance': 0.0,
                        'opening_carried_balance': 0.0,
                        'paid_to_carried_balance': 0.0,
                        'opening_due': 0.0,
                    }
                merged[sid]['total_due'] += float(row.get('total_due') or 0)
                merged[sid]['current_paid'] += float(row.get('paid_to_current_fees') or 0)
                merged[sid]['opening_carried_balance'] = max(
                    float(merged[sid]['opening_carried_balance'] or 0),
                    float(row.get('opening_carried_balance') or 0)
                )
                merged[sid]['paid_to_carried_balance'] = max(
                    float(merged[sid]['paid_to_carried_balance'] or 0),
                    float(row.get('paid_to_carried_balance') or 0)
                )
                merged[sid]['total_paid'] = (
                    float(merged[sid]['current_paid'] or 0)
                    + float(merged[sid]['paid_to_carried_balance'] or 0)
                )
        balances = []
        for item in merged.values():
            allocation = FinancialManager._allocate_opening_balance(
                total_current_fees=float(item['total_due']),
                total_paid=float(item['total_paid']),
                opening_carried_balance=float(item['opening_carried_balance']),
                carried_paid=float(item['paid_to_carried_balance']),
                current_paid=float(item['current_paid'])
            )
            balances.append({
                'student_id': item['student_id'],
                'student_code': item['student_code'],
                'student_name': item['student_name'],
                'class': item['class'],
                'total_due': item['total_due'],
                'total_paid': item['total_paid'],
                'carried_balance': allocation['remaining_carried_balance'],
                'opening_carried_balance': allocation['opening_carried_balance'],
                'paid_to_carried_balance': allocation['paid_to_carried_balance'],
                'opening_due': allocation['opening_due'],
                'balance': allocation['balance']
            })
    else:
        balances = []

    data = []
    for row in balances:
        if class_filter != 'All' and row.get('class') != class_filter:
            continue

        balance = float(row.get('balance') or 0)
        current_fee_due = float(row.get('total_due') or 0)
        carried_balance = float(row.get('carried_balance') or 0)
        opening_carried_balance = float(row.get('opening_carried_balance') or carried_balance or 0)
        paid_to_carried_balance = float(row.get('paid_to_carried_balance') or 0)
        opening_due = float(row.get('opening_due') or (current_fee_due + opening_carried_balance))
        total_paid = float(row.get('total_paid') or 0)
        if balance_filter == 'With Balance Only' and balance <= 0:
            continue
        if balance_filter == 'Cleared Only' and balance > 0:
            continue
        if balance_filter == 'Unpaid Only' and not (balance > 0 and total_paid <= 0):
            continue
        if balance_filter == 'Partial Only' and not (balance > 0 and total_paid > 0):
            continue
        if balance_filter == 'Carried Forward Only' and opening_carried_balance <= 0:
            continue

        data.append({
            'student_id': row.get('student_id'),
            'student_code': row.get('student_code'),
            'student_name': row.get('student_name'),
            'class': row.get('class'),
            'current_fee_due': current_fee_due,
            'carried_balance': carried_balance,
            'opening_carried_balance': opening_carried_balance,
            'paid_to_carried_balance': paid_to_carried_balance,
            'opening_due': opening_due,
            'total_paid': total_paid,
            'balance': balance
        })

    data.sort(key=lambda r: (r.get('class') or '', r.get('student_name') or '', -float(r.get('balance') or 0)))

    carried_forward_rows = [row for row in data if float(row.get('opening_carried_balance') or 0) > 0]

    total_current_due = sum(float(row['current_fee_due']) for row in data) if data else 0
    total_carried = sum(float(row['opening_carried_balance']) for row in data) if data else 0
    total_due = sum(float(row['opening_due']) for row in data) if data else 0
    total_paid = sum(float(row['total_paid']) for row in data) if data else 0
    total_balance = sum(float(row['balance']) for row in data) if data else 0

    return {
        'academic_year': academic_year,
        'term': term,
        'class_filter': class_filter,
        'balance_filter': balance_filter,
        'fee_type_filter': fee_type_filter,
        'summary': {
            'total_students': len(data),
            'students_with_carried_balance': len(carried_forward_rows),
            'total_current_fee_due': total_current_due,
            'total_carried_forward': total_carried,
            'total_opening_due': total_due,
            'total_paid': total_paid,
            'total_balance': total_balance,
        },
        'carried_forward_rows': carried_forward_rows,
        'current_fee_rows': data,
    }

def generate_student_fees_report(filename, class_filter="All", balance_filter="All", academic_year=None, fee_type_filter="All Fee Types", term=None):
    """Generate student fees report."""
    report = build_student_fees_report_data(
        academic_year=academic_year,
        class_filter=class_filter,
        balance_filter=balance_filter,
        fee_type_filter=fee_type_filter,
        term=term,
    )

    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    data = report.get('current_fee_rows') or []
    carried_rows = report.get('carried_forward_rows') or []
    summary = report.get('summary') or {}
    academic_year = report.get('academic_year') or academic_year or config.Config.CURRENT_ACADEMIC_YEAR
    term = report.get('term') or term or config.Config.CURRENT_TERM
    
    # Create story
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1
    )
    
    story.append(Paragraph(f"STUDENT FEES REPORT", title_style))
    story.append(Paragraph(f"Academic Year: {academic_year} | Term: {term}", styles['Normal']))
    story.append(Paragraph(f"Class Filter: {class_filter} | Balance Filter: {balance_filter} | Fee Filter: {fee_type_filter}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Total Students:', summary.get('total_students', 0)],
        ['Students With Carried Forward Balance:', summary.get('students_with_carried_balance', 0)],
        ['Current Term Fees Due:', format_currency(summary.get('total_current_fee_due', 0))],
        ['Carried Forward Fees:', format_currency(summary.get('total_carried_forward', 0))],
        ['Opening Fees Due:', format_currency(summary.get('total_opening_due', 0))],
        ['Total Fees Paid:', format_currency(summary.get('total_paid', 0))],
        ['Total Balance:', format_currency(summary.get('total_balance', 0))]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))

    if carried_rows:
        story.append(Paragraph("Carried Forward Fee Breakdown", styles['Heading2']))
        carried_table_data = [['Student Code', 'Name', 'Class', 'Carried Forward', 'Current Fee Due', 'Opening Due', 'Balance']]
        for row in carried_rows:
            carried_table_data.append([
                row['student_code'],
                row['student_name'],
                row['class'],
                format_currency(float(row['carried_balance'])),
                format_currency(float(row['current_fee_due'])),
                format_currency(float(row['opening_due'])),
                format_currency(float(row['balance']))
            ])

        carried_table = Table(carried_table_data, colWidths=[0.8*inch, 1.5*inch, 0.8*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.0*inch])
        carried_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(carried_table)
        story.append(Spacer(1, 20))

    # Main data table
    if data:
        story.append(Paragraph("Current Fee Report", styles['Heading2']))
        simple_table_data = [['Student Code', 'Name', 'Class', 'Current Fee Due', 'Carried Forward', 'Opening Due', 'Paid', 'Balance']]
        for row in data:
            simple_table_data.append([
                row['student_code'],
                row['student_name'],
                row['class'],
                format_currency(float(row['current_fee_due'])),
                format_currency(float(row['carried_balance'])),
                format_currency(float(row['opening_due'])),
                format_currency(float(row['total_paid'])),
                format_currency(float(row['balance']))
            ])
        
        table = Table(simple_table_data, colWidths=[0.8*inch, 1.4*inch, 0.7*inch, 1.0*inch, 1.0*inch, 1.0*inch, 0.9*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        # Color rows based on balance
        for i in range(1, len(simple_table_data)):
            balance_val = float(parse_currency(simple_table_data[i][7]))
            if balance_val > 0:
                table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.red)]))
            elif balance_val < 0:
                table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.green)]))
        
        story.append(table)
    else:
        story.append(Paragraph("No data found for the selected criteria.", styles['Normal']))
    
    # Footer note
    story.append(Spacer(1, 20))
    story.append(Paragraph("* Red indicates outstanding balance, Green indicates credit balance", 
                          ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)))
    
    # Build PDF
    doc.build(story)
