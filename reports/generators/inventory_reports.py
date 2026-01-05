"""
Inventory report generators
"""
from datetime import datetime, date
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import config
from database.connection import db

def generate_inventory_list_report(filename, category_filter="All"):
    """Generate inventory list report"""
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
            item_code,
            item_name,
            category,
            quantity,
            unit_price,
            total_value,
            min_quantity,
            max_quantity,
            location,
            supplier,
            last_restocked
        FROM inventory_items
        WHERE 1=1
    """
    
    conditions = []
    values = []
    
    if category_filter != 'All':
        conditions.append("category = %s")
        values.append(category_filter)
    
    if conditions:
        query += " AND " + " AND ".join(conditions)
    
    query += " ORDER BY category, item_name"
    
    data = db.execute_query(query, values, fetch=True)
    
    # Calculate totals
    total_items = len(data)
    total_quantity = sum(row['quantity'] for row in data) if data else 0
    total_value = sum(float(row['total_value']) for row in data) if data else 0
    
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
    
    story.append(Paragraph(f"INVENTORY LIST REPORT", title_style))
    story.append(Paragraph(f"School: {config.Config.SCHOOL_NAME}", styles['Normal']))
    story.append(Paragraph(f"Category Filter: {category_filter}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Total Items:', total_items],
        ['Total Quantity:', total_quantity],
        ['Total Value:', f"${total_value:,.2f}"],
        ['Category Filter:', category_filter]
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
        # Group by category
        categories = {}
        for row in data:
            category = row['category'] or 'Uncategorized'
            if category not in categories:
                categories[category] = []
            categories[category].append(row)
        
        for category, items in categories.items():
            # Category header
            story.append(Paragraph(f"Category: {category}", styles['Heading2']))
            story.append(Spacer(1, 10))
            
            # Prepare table data
            table_data = [['Code', 'Item Name', 'Qty', 'Unit Price', 'Total Value', 'Min', 'Max', 'Location']]
            
            for row in items:
                # Check for low stock
                is_low_stock = row['quantity'] < row['min_quantity']
                
                table_data.append([
                    row['item_code'],
                    row['item_name'],
                    row['quantity'],
                    f"${row['unit_price']:,.2f}" if row['unit_price'] else '',
                    f"${float(row['total_value']):,.2f}" if row['total_value'] else '',
                    row['min_quantity'],
                    row['max_quantity'],
                    row['location'] or ''
                ])
            
            # Create table
            table = Table(table_data, colWidths=[0.8*inch, 1.5*inch, 0.5*inch, 0.8*inch, 0.9*inch, 0.5*inch, 0.5*inch, 0.8*inch])
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
            
            # Highlight low stock items
            for i in range(1, len(table_data)):
                quantity = items[i-1]['quantity']
                min_quantity = items[i-1]['min_quantity']
                if quantity < min_quantity:
                    table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.red)]))
                    table.setStyle(TableStyle([('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold')]))
            
            story.append(table)
            story.append(Spacer(1, 20))
    else:
        story.append(Paragraph("No inventory items found for the selected criteria.", styles['Normal']))
    
    # Build PDF
    doc.build(story)

def generate_low_stock_report(filename):
    """Generate low stock report"""
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
            item_code,
            item_name,
            category,
            quantity,
            min_quantity,
            unit_price,
            total_value,
            (min_quantity - quantity) as reorder_quantity,
            supplier,
            last_restocked
        FROM inventory_items
        WHERE quantity < min_quantity
        ORDER BY (min_quantity - quantity) DESC
    """
    
    data = db.execute_query(query, fetch=True)
    
    # Calculate totals
    total_items = len(data)
    total_reorder_qty = sum(row['reorder_quantity'] for row in data) if data else 0
    total_reorder_cost = sum(float(row['reorder_quantity']) * float(row['unit_price']) 
                           for row in data if row['unit_price']) if data else 0
    
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
    
    story.append(Paragraph(f"LOW STOCK REPORT", title_style))
    story.append(Paragraph(f"School: {config.Config.SCHOOL_NAME}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Paragraph(f"*** URGENT ATTENTION REQUIRED ***", 
                          ParagraphStyle('Warning', parent=styles['Normal'], textColor=colors.red)))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Low Stock Items:', total_items],
        ['Total Reorder Quantity:', total_reorder_qty],
        ['Estimated Reorder Cost:', f"${total_reorder_cost:,.2f}"],
        ['Report Date:', date.today().strftime('%Y-%m-%d')]
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
        table_data = [['Item Code', 'Item Name', 'Category', 'Current Qty', 'Min Qty', 'Reorder Qty', 
                      'Unit Price', 'Reorder Cost', 'Supplier']]
        
        for row in data:
            reorder_qty = row['reorder_quantity']
            unit_price = float(row['unit_price']) if row['unit_price'] else 0
            reorder_cost = reorder_qty * unit_price
            
            table_data.append([
                row['item_code'],
                row['item_name'],
                row['category'],
                row['quantity'],
                row['min_quantity'],
                reorder_qty,
                f"${unit_price:,.2f}" if unit_price else '',
                f"${reorder_cost:,.2f}" if reorder_cost else '',
                row['supplier'] or ''
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.8*inch, 1.2*inch, 0.8*inch, 0.6*inch, 0.6*inch, 
                                            0.7*inch, 0.7*inch, 0.8*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        # Color code by severity
        for i in range(1, len(table_data)):
            current_qty = table_data[i][3]
            min_qty = table_data[i][4]
            reorder_qty = table_data[i][5]
            
            # Calculate percentage
            if min_qty > 0:
                percentage = (current_qty / min_qty) * 100
                if percentage < 25:
                    table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.red)]))
                    table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.white)]))
                elif percentage < 50:
                    table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.orange)]))
                elif percentage < 75:
                    table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.yellow)]))
        
        story.append(table)
        
        # Recommendations
        story.append(Spacer(1, 20))
        story.append(Paragraph("RECOMMENDATIONS:", styles['Heading2']))
        story.append(Paragraph("1. Order the above items immediately to avoid stockouts.", styles['Normal']))
        story.append(Paragraph("2. Contact suppliers for bulk pricing if available.", styles['Normal']))
        story.append(Paragraph("3. Review minimum quantities and adjust if necessary.", styles['Normal']))
        story.append(Paragraph("4. Consider alternative suppliers for better pricing.", styles['Normal']))
        
    else:
        story.append(Paragraph("No low stock items found. Inventory levels are adequate.", 
                              ParagraphStyle('Good', parent=styles['Normal'], textColor=colors.green)))
    
    # Build PDF
    doc.build(story)

def generate_inventory_valuation_report(filename):
    """Generate inventory valuation report"""
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
            category,
            COUNT(*) as item_count,
            SUM(quantity) as total_quantity,
            SUM(total_value) as total_value
        FROM inventory_items
        GROUP BY category
        ORDER BY total_value DESC
    """
    
    data = db.execute_query(query, fetch=True)
    
    # Calculate totals
    total_categories = len(data)
    total_items = sum(row['item_count'] for row in data) if data else 0
    total_quantity = sum(row['total_quantity'] for row in data) if data else 0
    total_value = sum(float(row['total_value']) for row in data) if data else 0
    
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
    
    story.append(Paragraph(f"INVENTORY VALUATION REPORT", title_style))
    story.append(Paragraph(f"School: {config.Config.SCHOOL_NAME}", styles['Normal']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Overall summary
    overall_data = [
        ['Total Categories:', total_categories],
        ['Total Items:', total_items],
        ['Total Quantity:', total_quantity],
        ['Total Inventory Value:', f"${total_value:,.2f}"]
    ]
    
    overall_table = Table(overall_data, colWidths=[2*inch, 2*inch])
    overall_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(overall_table)
    story.append(Spacer(1, 20))
    
    # Category breakdown
    if data:
        # Prepare table data
        table_data = [['Category', 'Item Count', 'Total Quantity', 'Total Value', '% of Total']]
        
        for row in data:
            category_value = float(row['total_value'])
            percentage = (category_value / total_value * 100) if total_value > 0 else 0
            
            table_data.append([
                row['category'] or 'Uncategorized',
                row['item_count'],
                row['total_quantity'],
                f"${category_value:,.2f}",
                f"{percentage:.1f}%"
            ])
        
        # Create table
        table = Table(table_data, colWidths=[1.5*inch, 0.8*inch, 1*inch, 1*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        # Color code by value
        for i in range(1, len(table_data)):
            percentage_str = table_data[i][4].replace('%', '')
            try:
                percentage = float(percentage_str)
                if percentage > 30:
                    table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.blue)]))
                    table.setStyle(TableStyle([('TEXTCOLOR', (0, i), (-1, i), colors.white)]))
                elif percentage > 15:
                    table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.lightblue)]))
            except:
                pass
        
        story.append(Paragraph("Category Breakdown", styles['Heading2']))
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Analysis
        story.append(Paragraph("INVENTORY ANALYSIS:", styles['Heading2']))
        
        # Find top categories
        if len(data) >= 3:
            top_categories = sorted(data, key=lambda x: float(x['total_value']), reverse=True)[:3]
            
            analysis_text = f"Top 3 categories by value:\n"
            for i, cat in enumerate(top_categories, 1):
                percentage = (float(cat['total_value']) / total_value * 100) if total_value > 0 else 0
                analysis_text += f"{i}. {cat['category']}: ${float(cat['total_value']):,.2f} ({percentage:.1f}%)\n"
            
            story.append(Paragraph(analysis_text, styles['Normal']))
        
        # Recommendations
        story.append(Spacer(1, 10))
        story.append(Paragraph("RECOMMENDATIONS:", styles['Heading3']))
        story.append(Paragraph("1. Review high-value categories for insurance coverage.", styles['Normal']))
        story.append(Paragraph("2. Consider bulk purchasing for high-usage categories.", styles['Normal']))
        story.append(Paragraph("3. Implement tighter security for valuable inventory.", styles['Normal']))
        story.append(Paragraph("4. Regularly audit high-value items.", styles['Normal']))
        
    else:
        story.append(Paragraph("No inventory data found.", styles['Normal']))
    
    # Build PDF
    doc.build(story)