"""
Student report generators
"""
from datetime import datetime, date
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import config
from database.connection import db
from models.student import Student

def generate_student_list_report(filename, class_filter="All", status_filter="Active"):
    """Generate student list report"""
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
    query = """
        SELECT 
            s.student_code,
            CONCAT(s.first_name, ' ', s.last_name) as student_name,
            s.class,
            s.birth_date,
            s.parent_name,
            s.parent_phone,
            s.enrollment_date,
            CASE WHEN s.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status
        FROM students s
        WHERE 1=1
    """
    
    conditions = []
    values = []
    
    if status_filter == 'Active':
        conditions.append("s.is_active = 1")
    elif status_filter == 'Inactive':
        conditions.append("s.is_active = 0")
    
    if class_filter != 'All':
        conditions.append("s.class = %s")
        values.append(class_filter)
    
    if conditions:
        query += " AND " + " AND ".join(conditions)
    
    query += " ORDER BY s.class, s.last_name, s.first_name"
    
    data = db.execute_query(query, values, fetch=True)
    
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
    
    story.append(Paragraph(f"STUDENT LIST REPORT", title_style))
    story.append(Paragraph(f"School: {config.Config.SCHOOL_NAME}", styles['Normal']))
    story.append(Paragraph(f"Class Filter: {class_filter} | Status: {status_filter}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Total Students:', len(data)],
        ['Active Students:', len([d for d in data if d['status'] == 'Active'])],
        ['Inactive Students:', len([d for d in data if d['status'] == 'Inactive'])]
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
        # Group by class
        classes = {}
        for row in data:
            class_name = row['class']
            if class_name not in classes:
                classes[class_name] = []
            classes[class_name].append(row)
        
        for class_name, class_students in classes.items():
            # Class header
            story.append(Paragraph(f"Class: {class_name}", styles['Heading2']))
            story.append(Paragraph(f"Student Count: {len(class_students)}", styles['Normal']))
            story.append(Spacer(1, 10))
            
            # Prepare table data
            table_data = [['Code', 'Name', 'Birth Date', 'Parent', 'Phone', 'Enrollment Date', 'Status']]
            
            for row in class_students:
                birth_date = row['birth_date'].strftime('%Y-%m-%d') if row['birth_date'] else ''
                enrollment_date = row['enrollment_date'].strftime('%Y-%m-%d') if row['enrollment_date'] else ''
                
                table_data.append([
                    row['student_code'],
                    row['student_name'],
                    birth_date,
                    row['parent_name'] or '',
                    row['parent_phone'] or '',
                    enrollment_date,
                    row['status']
                ])
            
            # Create table
            table = Table(table_data, colWidths=[0.7*inch, 1.5*inch, 0.8*inch, 1.2*inch, 1*inch, 0.9*inch, 0.6*inch])
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
            story.append(Spacer(1, 20))
            
            # Add page break if this isn't the last class
            if list(classes.keys()).index(class_name) < len(classes) - 1:
                story.append(PageBreak())
    else:
        story.append(Paragraph("No students found for the selected criteria.", styles['Normal']))
    
    # Build PDF
    doc.build(story)

def generate_attendance_summary_report(filename, start_date=None, end_date=None, class_filter="All"):
    """Generate attendance summary report"""
    if not start_date:
        start_date = date(date.today().year, 1, 1)
    if not end_date:
        end_date = date.today()
    
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
    query = """
        SELECT 
            a.attendance_date,
            COUNT(*) as total_students,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_count,
            SUM(CASE WHEN a.status = 'Late' THEN 1 ELSE 0 END) as late_count,
            SUM(CASE WHEN a.status = 'Excused' THEN 1 ELSE 0 END) as excused_count,
            ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) / COUNT(*)) * 100, 2) as attendance_rate
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.attendance_date BETWEEN %s AND %s
    """
    
    values = [start_date, end_date]
    
    if class_filter != 'All':
        query += " AND s.class = %s"
        values.append(class_filter)
    
    query += """
        GROUP BY a.attendance_date
        ORDER BY a.attendance_date DESC
    """
    
    data = db.execute_query(query, values, fetch=True)
    
    # Calculate totals
    total_days = len(data)
    total_students = sum(row['total_students'] for row in data) if data else 0
    total_present = sum(row['present_count'] for row in data) if data else 0
    
    overall_rate = (total_present / total_students * 100) if total_students > 0 else 0
    
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
    
    story.append(Paragraph(f"ATTENDANCE SUMMARY REPORT", title_style))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
    story.append(Paragraph(f"Class Filter: {class_filter}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Total Days:', total_days],
        ['Total Student-Days:', total_students],
        ['Total Present:', total_present],
        ['Overall Attendance Rate:', f"{overall_rate:.2f}%"]
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
    
    # Daily breakdown
    if data:
        # Prepare table data
        table_data = [['Date', 'Total', 'Present', 'Absent', 'Late', 'Excused', 'Rate']]
        
        for row in data:
            table_data.append([
                row['attendance_date'].strftime('%Y-%m-%d') if row['attendance_date'] else '',
                row['total_students'],
                row['present_count'],
                row['absent_count'],
                row['late_count'],
                row['excused_count'],
                f"{row['attendance_rate']}%"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[1*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.7*inch])
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
        
        # Color code attendance rates
        for i in range(1, len(table_data)):
            rate_str = table_data[i][6].replace('%', '')
            try:
                rate = float(rate_str)
                if rate >= 90:
                    table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.green)]))
                elif rate >= 80:
                    table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.orange)]))
                else:
                    table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.red)]))
            except:
                pass
        
        story.append(Paragraph("Daily Attendance Breakdown", styles['Heading2']))
        story.append(table)
    else:
        story.append(Paragraph("No attendance data found for the selected period.", styles['Normal']))
    
    # Build PDF
    doc.build(story)

def generate_student_attendance_report(filename, student_id, start_date=None, end_date=None):
    """Generate individual student attendance report"""
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
    
    # Get student info
    student_query = """
        SELECT 
            student_code,
            CONCAT(first_name, ' ', last_name) as student_name,
            class,
            parent_name,
            parent_phone,
            enrollment_date
        FROM students
        WHERE student_id = %s
    """
    
    student_info = db.execute_query(student_query, (student_id,), fetch=True)
    
    if not student_info:
        return
    
    student_info = student_info[0]
    
    # Get attendance data
    attendance_query = """
        SELECT 
            attendance_date,
            status,
            check_in_time,
            check_out_time,
            remarks
        FROM attendance
        WHERE student_id = %s
            AND attendance_date BETWEEN %s AND %s
        ORDER BY attendance_date DESC
    """
    
    attendance_data = db.execute_query(attendance_query, (student_id, start_date, end_date), fetch=True)
    
    # Calculate statistics
    total_days = len(attendance_data)
    present_days = len([d for d in attendance_data if d['status'] == 'Present'])
    absent_days = len([d for d in attendance_data if d['status'] == 'Absent'])
    late_days = len([d for d in attendance_data if d['status'] == 'Late'])
    excused_days = len([d for d in attendance_data if d['status'] == 'Excused'])
    
    attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
    
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
    
    story.append(Paragraph(f"STUDENT ATTENDANCE REPORT", title_style))
    story.append(Paragraph(f"Student: {student_info['student_name']} ({student_info['student_code']})", styles['Normal']))
    story.append(Paragraph(f"Class: {student_info['class']} | Period: {start_date} to {end_date}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Student information
    info_data = [
        ['Student Code:', student_info['student_code']],
        ['Full Name:', student_info['student_name']],
        ['Class:', student_info['class']],
        ['Parent/Guardian:', student_info['parent_name'] or ''],
        ['Phone:', student_info['parent_phone'] or ''],
        ['Enrollment Date:', student_info['enrollment_date'].strftime('%Y-%m-%d') if student_info['enrollment_date'] else '']
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Attendance statistics
    stats_data = [
        ['Total Days:', total_days],
        ['Present Days:', present_days],
        ['Absent Days:', absent_days],
        ['Late Days:', late_days],
        ['Excused Days:', excused_days],
        ['Attendance Rate:', f"{attendance_rate:.2f}%"]
    ]
    
    stats_table = Table(stats_data, colWidths=[1.5*inch, 1.5*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(Paragraph("Attendance Statistics", styles['Heading2']))
    story.append(stats_table)
    story.append(Spacer(1, 20))
    
    # Attendance details
    if attendance_data:
        # Prepare table data
        table_data = [['Date', 'Status', 'Check In', 'Check Out', 'Remarks']]
        
        for row in attendance_data:
            check_in = row['check_in_time'].strftime('%H:%M') if row['check_in_time'] else ''
            check_out = row['check_out_time'].strftime('%H:%M') if row['check_out_time'] else ''
            
            table_data.append([
                row['attendance_date'].strftime('%Y-%m-%d') if row['attendance_date'] else '',
                row['status'],
                check_in,
                check_out,
                row['remarks'] or ''
            ])
        
        # Create table
        table = Table(table_data, colWidths=[1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 2*inch])
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
        
        # Color code status
        for i in range(1, len(table_data)):
            status = table_data[i][1]
            if status == 'Present':
                table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.green)]))
            elif status == 'Absent':
                table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.red)]))
            elif status == 'Late':
                table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.orange)]))
            elif status == 'Excused':
                table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.blue)]))
        
        story.append(Paragraph("Attendance Details", styles['Heading2']))
        story.append(table)
    else:
        story.append(Paragraph("No attendance records found for the selected period.", styles['Normal']))
    
    # Build PDF
    doc.build(story)