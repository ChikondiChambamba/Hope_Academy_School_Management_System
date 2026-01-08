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

def generate_expense_report(filename, start_date=None, end_date=None):
    """Generate expense report"""
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
    # Fee collections
    fee_query = """
        SELECT 
            MONTH(payment_date) as month,
            SUM(amount_paid) as total_fees,
            COUNT(*) as payment_count
        FROM student_fees
        WHERE YEAR(payment_date) = %s
        GROUP BY MONTH(payment_date)
        ORDER BY month
    """
    
    fee_data = db.execute_query(fee_query, (academic_year,), fetch=True)
    
    # Expenses
    expense_query = """
        SELECT 
            category,
            SUM(amount) as total_amount,
            COUNT(*) as expense_count
        FROM expenses
        WHERE YEAR(expense_date) = %s
        GROUP BY category
        ORDER BY total_amount DESC
    """
    
    expense_data = db.execute_query(expense_query, (academic_year,), fetch=True)
    
    # Calculate totals
    total_fees = sum(row['total_fees'] for row in fee_data) if fee_data else 0
    total_expenses = sum(row['total_amount'] for row in expense_data) if expense_data else 0
    net_balance = total_fees - total_expenses
    
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
    story.append(Paragraph(f"Academic Year: {academic_year} - {term if term else 'All Terms'}", styles['Normal']))
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
            month_name = months[row['month'] - 1] if 1 <= row['month'] <= 12 else f"Month {row['month']}"
            fee_table_data.append([
                month_name,
                format_currency(float(row['total_fees'])),
                row['payment_count']
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

def generate_student_fees_report(filename, class_filter="All", balance_filter="All", academic_year=None):
    """Generate student fees report"""
    if not academic_year:
        academic_year = config.Config.CURRENT_ACADEMIC_YEAR
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get data
    # Compute per-student totals by summing applicable fee types (respecting exemptions and
    # registration/uniform rules) and subtracting payments. Avoid CROSS JOIN which sums
    # every fee type for every student.
    query = """
        SELECT
            s.student_code,
            CONCAT(s.first_name, ' ', s.last_name) AS student_name,
            s.class,
            -- Sum expected amounts per student, zeroing-out exempted fees and fees that don't apply
            COALESCE(SUM(
                CASE
                    WHEN sfe.exemption_id IS NOT NULL THEN 0
                    WHEN (LOWER(ft.fee_name) LIKE '%registration%' OR LOWER(ft.fee_name) LIKE '%uniform%') AND s.is_new = 0 THEN 0
                    ELSE ft.amount
                END
            ), 0) AS total_due,
            COALESCE(SUM(sf.amount_paid), 0) AS total_paid,
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
        LEFT JOIN student_fees sf ON sf.student_id = s.student_id AND sf.fee_type_id = ft.fee_type_id
        WHERE s.is_active = 1
    """
    
    conditions = []
    values = [academic_year]
    
    if class_filter != 'All':
        conditions.append("s.class = %s")
        values.append(class_filter)
    
    if balance_filter == 'With Balance Only':
        conditions.append("COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) > 0")
    elif balance_filter == 'Cleared Only':
        conditions.append("COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) <= 0")
    
    if conditions:
        query += " AND " + " AND ".join(conditions)
    
    query += """
        GROUP BY s.student_id, s.student_code, s.first_name, s.last_name, s.class
        ORDER BY balance DESC, s.class, s.last_name
    """
    
    data = db.execute_query(query, values, fetch=True)
    
    # Calculate totals
    total_due = sum(float(row['total_due']) for row in data) if data else 0
    total_paid = sum(float(row['total_paid']) for row in data) if data else 0
    total_balance = sum(float(row['balance']) for row in data) if data else 0
    
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
    story.append(Paragraph(f"Academic Year: {academic_year}", styles['Normal']))
    story.append(Paragraph(f"Class Filter: {class_filter} | Balance Filter: {balance_filter}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Total Students:', len(data)],
        ['Total Fees Due:', format_currency(total_due)],
        ['Total Fees Paid:', format_currency(total_paid)],
        ['Total Balance:', format_currency(total_balance)]
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
        table_data = [['Student Code', 'Name', 'Class', 'Total Due', 'Paid', 'Balance']]
        
        for row in data:
            balance = float(row['balance'])
            balance_text = format_currency(balance)
            
            # Color code balances
            if balance > 0:
                balance_text = f"<font color='red'>{balance_text}</font>"
            elif balance < 0:
                balance_text = f"<font color='green'>{balance_text} (Credit)</font>"
            
                table_data.append([
                row['student_code'],
                row['student_name'],
                row['class'],
                format_currency(float(row['total_due'])),
                format_currency(float(row['total_paid'])),
                balance_text
            ])
        
        # Create table with Paragraph for HTML formatting
        from reportlab.platypus.flowables import KeepTogether
        
        story.append(Paragraph("Student Fee Balances", styles['Heading2']))
        
        # We need to handle the table differently due to HTML formatting
        # For simplicity, let's create a simpler table
        simple_table_data = [['Student Code', 'Name', 'Class', 'Total Due', 'Paid', 'Balance']]
        
        for row in data:
            simple_table_data.append([
                row['student_code'],
                row['student_name'],
                row['class'],
                format_currency(float(row['total_due'])),
                format_currency(float(row['total_paid'])),
                format_currency(float(row['balance']))
            ])
        
        table = Table(simple_table_data, colWidths=[0.8*inch, 1.5*inch, 0.7*inch, 1*inch, 1*inch, 1*inch])
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
            balance_val = float(parse_currency(simple_table_data[i][5]))
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