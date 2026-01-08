"""
PDF report generator for School Management System
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from datetime import datetime, date
import os
import config
from database.connection import db
from utils.helpers import format_currency, parse_currency

def create_header_footer(canvas, doc):
    """Create header and footer for PDF pages"""
    # Save the state of our canvas so we can draw on it
    canvas.saveState()
    
    # Header
    canvas.setFont('Helvetica-Bold', 16)
    canvas.drawString(inch, doc.height + inch, config.Config.SCHOOL_NAME)
    
    canvas.setFont('Helvetica', 10)
    canvas.drawString(inch, doc.height + inch - 15, config.Config.SCHOOL_ADDRESS)
    
    # Footer
    canvas.setFont('Helvetica', 8)
    canvas.drawString(inch, 0.5 * inch, f"Page {doc.page}")
    canvas.drawRightString(doc.width + inch, 0.5 * inch, 
                          f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Restore the state
    canvas.restoreState()

def generate_student_list_pdf(class_filter=None, output_file=None):
    """Generate PDF student list"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'student_list_{timestamp}.pdf')
    
    # Create PDF document
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        title='Student List'
    )
    
    # Get data
    if class_filter:
        query = """
            SELECT 
                student_code,
                CONCAT(first_name, ' ', last_name) as name,
                class,
                parent_name,
                parent_phone,
                enrollment_date
            FROM students
            WHERE is_active = 1 AND class = %s
            ORDER BY class, last_name, first_name
        """
        results = db.execute_query(query, (class_filter,), fetch=True)
        title = f"Student List - Class: {class_filter}"
    else:
        query = """
            SELECT 
                student_code,
                CONCAT(first_name, ' ', last_name) as name,
                class,
                parent_name,
                parent_phone,
                enrollment_date
            FROM students
            WHERE is_active = 1
            ORDER BY class, last_name, first_name
        """
        results = db.execute_query(query, fetch=True)
        title = "Student List - All Classes"
    
    # Prepare data for table
    data = [['Code', 'Name', 'Class', 'Parent', 'Phone', 'Enrollment Date']]
    
    for row in results:
        data.append([
            row['student_code'],
            row['name'],
            row['class'],
            row['parent_name'] or '',
            row['parent_phone'] or '',
            row['enrollment_date']
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    # Build document
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    elements.append(Paragraph(title, title_style))
    
    # Summary
    summary = f"Total Students: {len(results)} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Add table
    elements.append(table)
    
    # Generate PDF
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file

def generate_student_fees_report(start_date=None, end_date=None, class_filter=None, output_file=None):
    """Generate student fees report"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'student_fees_{timestamp}.pdf')
    
    # Build query based on filters
    query = """
        SELECT 
            s.student_code,
            CONCAT(s.first_name, ' ', s.last_name) as student_name,
            s.class,
            ft.fee_name,
            sf.amount_paid,
            sf.payment_date,
            sf.payment_method,
            sf.receipt_number
        FROM student_fees sf
        JOIN students s ON sf.student_id = s.student_id
        JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
        WHERE s.is_active = 1
    """
    
    params = []
    
    if start_date:
        query += " AND sf.payment_date >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND sf.payment_date <= %s"
        params.append(end_date)
    
    if class_filter:
        query += " AND s.class = %s"
        params.append(class_filter)
    
    query += " ORDER BY sf.payment_date DESC, s.class, s.last_name"
    
    results = db.execute_query(query, tuple(params), fetch=True)
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    
    # Prepare data
    data = [['Date', 'Student', 'Class', 'Fee Type', 'Amount', 'Method', 'Receipt']]
    
    total_amount = 0
    for row in results:
        data.append([
            row['payment_date'],
            row['student_name'],
            row['class'],
            row['fee_name'],
            format_currency(float(row['amount_paid'])),
            row['payment_method'],
            row['receipt_number'] or ''
        ])
        total_amount += float(row['amount_paid'])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    # Build document
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title = "Student Fees Report"
    if start_date or end_date or class_filter:
        title += " - Filtered"
    
    elements.append(Paragraph(title, styles['Heading1']))
    
    # Summary
    summary = f"Total Records: {len(results)} | Total Amount: {format_currency(total_amount)}"
    if start_date:
        summary += f" | From: {start_date}"
    if end_date:
        summary += f" | To: {end_date}"
    if class_filter:
        summary += f" | Class: {class_filter}"
    
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(table)
    
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file

def generate_attendance_report(start_date=None, end_date=None, class_filter=None, output_file=None):
    """Generate attendance report"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'attendance_{timestamp}.pdf')
    
    # Get attendance data
    query = """
        SELECT 
            a.attendance_date,
            s.student_code,
            CONCAT(s.first_name, ' ', s.last_name) as student_name,
            s.class,
            a.status,
            a.check_in_time,
            a.check_out_time,
            a.remarks
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE s.is_active = 1
    """
    
    params = []
    
    if start_date:
        query += " AND a.attendance_date >= %s"
        params.append(start_date)
    
    if end_date:
        query += " AND a.attendance_date <= %s"
        params.append(end_date)
    
    if class_filter:
        query += " AND s.class = %s"
        params.append(class_filter)
    
    query += " ORDER BY a.attendance_date DESC, s.class, s.last_name"
    
    results = db.execute_query(query, tuple(params), fetch=True)
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    
    # Prepare data
    data = [['Date', 'Student', 'Class', 'Status', 'Check-in', 'Check-out', 'Remarks']]
    
    for row in results:
        data.append([
            row['attendance_date'],
            row['student_name'],
            row['class'],
            row['status'],
            row['check_in_time'] or '',
            row['check_out_time'] or '',
            row['remarks'] or ''
        ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2196F3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    # Build document
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Attendance Report", styles['Heading1']))
    
    summary = f"Total Records: {len(results)}"
    if start_date:
        summary += f" | From: {start_date}"
    if end_date:
        summary += f" | To: {end_date}"
    if class_filter:
        summary += f" | Class: {class_filter}"
    
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(table)
    
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file

def generate_fee_collection_report(start_date=None, end_date=None, output_file=None):
    """Generate fee collection report"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()
    
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'fee_collection_{timestamp}.pdf')
    
    # Get fee collection summary
    query = """
        SELECT 
            DATE_FORMAT(payment_date, '%Y-%m') as month,
            COUNT(*) as payment_count,
            SUM(amount_paid) as total_amount
        FROM student_fees
        WHERE payment_date BETWEEN %s AND %s
        GROUP BY DATE_FORMAT(payment_date, '%Y-%m')
        ORDER BY month DESC
    """
    
    results = db.execute_query(query, (start_date, end_date), fetch=True)
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    
    # Prepare data
    data = [['Month', 'Payment Count', 'Total Amount']]
    
    grand_total = 0
    for row in results:
        data.append([
            row['month'],
            str(row['payment_count']),
            format_currency(float(row['total_amount']))
        ])
        grand_total += float(row['total_amount'])
    
    # Add total row
    data.append(['GRAND TOTAL', '', format_currency(grand_total)])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF9800')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFEB3B')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))
    
    # Build document
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Fee Collection Report", styles['Heading1']))
    elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(table)
    
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file

def generate_expense_report(start_date=None, end_date=None, output_file=None):
    """Generate expense report"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()
    
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'expenses_{timestamp}.pdf')
    
    # Get expense summary by category
    query = """
        SELECT 
            category,
            COUNT(*) as expense_count,
            SUM(amount) as total_amount
        FROM expenses
        WHERE expense_date BETWEEN %s AND %s
        GROUP BY category
        ORDER BY total_amount DESC
    """
    
    results = db.execute_query(query, (start_date, end_date), fetch=True)
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    
    # Prepare data
    data = [['Category', 'Count', 'Total Amount']]
    
    grand_total = 0
    for row in results:
        data.append([
            row['category'] or 'Uncategorized',
            str(row['expense_count']),
            format_currency(float(row['total_amount']))
        ])
        grand_total += float(row['total_amount'])

    # Add total row
    data.append(['TOTAL', '', format_currency(grand_total)])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F44336')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFCDD2')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))
    
    # Build document
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Expense Report", styles['Heading1']))
    elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(table)
    
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file

def generate_financial_summary_report(start_date=None, end_date=None, output_file=None):
    """Generate complete financial summary report"""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()
    
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'financial_summary_{timestamp}.pdf')
    
    # Get financial data
    from models.finance import FinancialManager
    summary = FinancialManager.get_financial_summary(start_date, end_date)
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    elements.append(Paragraph("Financial Summary Report", styles['Heading1']))
    elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
    elements.append(Spacer(1, 30))
    
    # Summary table
    summary_data = [
        ['Category', 'Amount'],
        ['Total Fees Collected', format_currency(summary['revenue']['total_fees'])],
        ['Total Expenses', format_currency(summary['expenses']['total_expenses'])],
        ['Net Balance', format_currency(summary['net_balance'])],
        ['Outstanding Fees', format_currency(summary['outstanding_fees'])]
    ]
    
    summary_table = Table(summary_data, colWidths=[200, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#673AB7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Monthly breakdown
    if summary['revenue']['monthly_breakdown']:
        elements.append(Paragraph("Monthly Fee Collection", styles['Heading2']))
        
        monthly_data = [['Month', 'Payments', 'Amount']]
        for month in summary['revenue']['monthly_breakdown']:
            monthly_data.append([
                f"{month['year']}-{month['month']:02d}",
                str(month['payment_count']),
                f"${month['total_amount']:,.2f}"
            ])
        
        monthly_table = Table(monthly_data)
        monthly_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#009688')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(monthly_table)
    
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file

def generate_inventory_report(output_file=None):
    """Generate inventory report"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'inventory_{timestamp}.pdf')
    
    # Get inventory data
    from models.inventory import InventoryItem
    items = InventoryItem.get_all()
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    
    # Prepare data
    data = [['Code', 'Name', 'Category', 'Quantity', 'Unit Price', 'Total Value']]
    
    total_value = 0
    for item in items:
        data.append([
            item.item_code,
            item.item_name,
            item.category,
            str(item.quantity),
            f"${item.unit_price:,.2f}" if item.unit_price else "$0.00",
            f"${item.total_value:,.2f}" if item.total_value else "$0.00"
        ])
        total_value += item.total_value if item.total_value else 0
    
    # Add total row
    data.append(['', '', '', '', 'TOTAL:', f"${total_value:,.2f}"])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#795548')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (4, 1), (5, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#D7CCC8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))
    
    # Build document
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Inventory Report", styles['Heading1']))
    elements.append(Paragraph(f"Total Items: {len(items)} | Total Value: ${total_value:,.2f}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(table)
    
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file

def generate_low_stock_report(output_file=None):
    """Generate low stock report"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'low_stock_{timestamp}.pdf')
    
    # Get low stock items
    from models.inventory import InventoryItem
    items = InventoryItem.get_low_stock_items()
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    
    # Prepare data
    data = [['Code', 'Name', 'Category', 'Current', 'Min', 'Reorder Qty', 'Unit Price', 'Reorder Cost']]
    
    total_reorder_cost = 0
    for item in items:
        reorder_qty = item.get_reorder_quantity()
        reorder_cost = reorder_qty * (item.unit_price or 0)
        total_reorder_cost += reorder_cost
        
        data.append([
            item.item_code,
            item.item_name,
            item.category,
            str(item.quantity),
            str(item.min_quantity),
            str(reorder_qty),
            f"${item.unit_price:,.2f}" if item.unit_price else "$0.00",
            f"${reorder_cost:,.2f}"
        ])
    
    # Add total row
    data.append(['', '', '', '', '', '', 'TOTAL:', f"${total_reorder_cost:,.2f}"])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF5722')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (6, 1), (7, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFCCBC')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))
    
    # Build document
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Low Stock Alert Report", styles['Heading1']))
    elements.append(Paragraph(f"Items below minimum quantity: {len(items)} | Total reorder cost: ${total_reorder_cost:,.2f}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(table)
    
    # Add note
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Note: Please reorder the above items to maintain sufficient stock levels.", styles['Italic']))
    
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file

def generate_balances_pdf(output_file=None):
    """Generate student balances PDF"""
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(config.Config.PATHS['exports'], f'student_balances_{timestamp}.pdf')
    
    # Get student balances
    from models.finance import FinancialManager
    balances = FinancialManager.get_student_balances()
    
    # Create PDF
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    
    # Prepare data
    data = [['Student', 'Class', 'Total Due', 'Amount Paid', 'Balance']]
    
    total_due = total_paid = total_balance = 0
    for balance in balances:
        data.append([
            balance['student_name'],
            balance['class'],
            f"${balance['total_due']:,.2f}",
            f"${balance['total_paid']:,.2f}",
            f"${balance['balance']:,.2f}"
        ])
        total_due += float(balance['total_due'])
        total_paid += float(balance['total_paid'])
        total_balance += float(balance['balance'])
    
    # Add totals
    data.append(['TOTALS:', '', f"${total_due:,.2f}", f"${total_paid:,.2f}", f"${total_balance:,.2f}"])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3F51B5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#C5CAE9')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))
    
    # Build document
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Student Fee Balances Report", styles['Heading1']))
    elements.append(Paragraph(f"Academic Year: {config.Config.CURRENT_ACADEMIC_YEAR} | Total Outstanding: ${total_balance:,.2f}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(table)
    
    doc.build(elements, onFirstPage=create_header_footer, onLaterPages=create_header_footer)
    
    return output_file