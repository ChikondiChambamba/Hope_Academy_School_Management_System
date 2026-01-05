"""
Reports Tab - UI for generating various reports
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta
import config
from database.connection import db
from reports.generators.financial_reports import (
    generate_fee_collection_report,
    generate_expense_report,
    generate_financial_summary_report,
    generate_student_fees_report
)
from reports.generators.student_reports import (
    generate_student_list_report,
    generate_attendance_summary_report,
    generate_student_attendance_report
)
from reports.generators.inventory_reports import (
    generate_inventory_list_report,
    generate_low_stock_report,
    generate_inventory_valuation_report
)
from UI.dialogs import DateRangeDialog, StudentSelectionDialog

class ReportsTab:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        self.current_report = None
        self.report_params = {}
    
    def setup_ui(self):
        """Setup reports tab UI"""
        # Main container
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(
            main_container, 
            text="Report Generator",
            style='Title.TLabel'
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Description
        desc_label = ttk.Label(
            main_container,
            text="Generate various reports for school management",
            font=('Arial', 10)
        )
        desc_label.pack(anchor='w', pady=(0, 20))
        
        # Create main content area with two panels
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill='both', expand=True)
        
        # Left panel - Report Categories
        left_panel = ttk.Frame(content_frame, width=300)
        left_panel.pack(side='left', fill='y', padx=(0, 10))
        left_panel.pack_propagate(False)
        
        self.setup_report_categories(left_panel)
        
        # Right panel - Report Configuration
        right_panel = ttk.Frame(content_frame)
        right_panel.pack(side='left', fill='both', expand=True)
        
        self.setup_report_configuration(right_panel)
        
        # Status bar
        self.status_frame = ttk.Frame(main_container)
        self.status_frame.pack(fill='x', pady=(10, 0))
        
        self.status_label = ttk.Label(self.status_frame, text="")
        self.status_label.pack(side='left')
    
    def setup_report_categories(self, parent):
        """Setup report categories treeview"""
        # Category label
        cat_label = ttk.Label(
            parent, 
            text="Report Categories",
            style='Header.TLabel'
        )
        cat_label.pack(anchor='w', pady=(0, 10))
        
        # Create treeview for categories
        self.category_tree = ttk.Treeview(
            parent,
            height=20,
            selectmode='browse',
            show='tree'
        )
        
        # Add categories and reports
        self.setup_category_tree()
        
        # Add scrollbar
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.category_tree.yview)
        self.category_tree.configure(yscrollcommand=vsb.set)
        
        self.category_tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        
        # Bind selection event
        self.category_tree.bind('<<TreeviewSelect>>', self.on_category_select)
    
    def setup_category_tree(self):
        """Setup category tree structure"""
        # Define categories and reports
        categories = {
            'Financial Reports': [
                ('fee_collection', 'Fee Collection Report'),
                ('expense', 'Expense Report'),
                ('financial_summary', 'Financial Summary'),
                ('student_fees', 'Student Fees Report')
            ],
            'Student Reports': [
                ('student_list', 'Student List'),
                ('attendance_summary', 'Attendance Summary'),
                ('student_attendance', 'Individual Student Attendance')
            ],
            'Inventory Reports': [
                ('inventory_list', 'Inventory List'),
                ('low_stock', 'Low Stock Report'),
                ('inventory_valuation', 'Inventory Valuation')
            ],
            'Academic Reports': [
                ('class_list', 'Class List'),
                ('teacher_assignments', 'Teacher Assignments')
            ]
        }
        
        # Add categories to tree
        for category, reports in categories.items():
            cat_id = self.category_tree.insert('', 'end', text=category, open=True)
            
            for report_id, report_name in reports:
                self.category_tree.insert(cat_id, 'end', iid=report_id, text=report_name)
    
    def setup_report_configuration(self, parent):
        """Setup report configuration panel"""
        # Header
        self.config_header = ttk.Label(
            parent, 
            text="Select a report from the left panel",
            style='Header.TLabel'
        )
        self.config_header.pack(anchor='w', pady=(0, 10))
        
        # Description
        self.config_desc = ttk.Label(
            parent,
            text="",
            wraplength=500,
            justify='left'
        )
        self.config_desc.pack(anchor='w', pady=(0, 20))
        
        # Configuration frame
        self.config_frame = ttk.Frame(parent)
        self.config_frame.pack(fill='x', pady=(0, 20))
        
        # Initially hide config frame
        self.config_frame.pack_forget()
        
        # Action buttons frame
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill='x')
        
        # Preview button
        self.preview_btn = ttk.Button(
            action_frame,
            text="Preview Report",
            command=self.preview_report,
            state='disabled',
            style='Primary.TButton'
        )
        self.preview_btn.pack(side='left', padx=(0, 10))
        
        # Generate PDF button
        self.generate_pdf_btn = ttk.Button(
            action_frame,
            text="Generate PDF",
            command=self.generate_pdf,
            state='disabled',
            style='Success.TButton'
        )
        self.generate_pdf_btn.pack(side='left', padx=(0, 10))
        
        # Generate Excel button
        self.generate_excel_btn = ttk.Button(
            action_frame,
            text="Generate Excel",
            command=self.generate_excel,
            state='disabled'
        )
        self.generate_excel_btn.pack(side='left')
    
    def on_category_select(self, event):
        """Handle report category selection"""
        selected = self.category_tree.selection()
        
        if not selected:
            return
        
        item = selected[0]
        
        # Check if it's a report (not a category)
        parent = self.category_tree.parent(item)
        if parent == '':
            # Category selected, not a report
            self.current_report = None
            self.update_config_panel("Select a specific report from the list")
            return
        
        # Get report ID
        report_id = item
        self.current_report = report_id
        self.report_params = {}
        
        # Update configuration panel based on report type
        self.update_config_panel_for_report(report_id)
    
    def update_config_panel(self, message):
        """Update configuration panel with message"""
        self.config_header.config(text="Report Configuration")
        self.config_desc.config(text=message)
        
        # Hide configuration frame
        self.config_frame.pack_forget()
        
        # Disable action buttons
        self.preview_btn.state(['disabled'])
        self.generate_pdf_btn.state(['disabled'])
        self.generate_excel_btn.state(['disabled'])
    
    def update_config_panel_for_report(self, report_id):
        """Update configuration panel for specific report"""
        report_configs = {
            'fee_collection': {
                'name': 'Fee Collection Report',
                'description': 'Generate report of all fee payments within a date range.',
                'config': self.setup_date_range_config
            },
            'expense': {
                'name': 'Expense Report',
                'description': 'Generate report of all expenses within a date range.',
                'config': self.setup_date_range_config
            },
            'financial_summary': {
                'name': 'Financial Summary',
                'description': 'Generate comprehensive financial summary including revenue, expenses, and net balance.',
                'config': self.setup_term_config
            },
            'student_fees': {
                'name': 'Student Fees Report',
                'description': 'Generate report of student fee balances and payment history.',
                'config': self.setup_student_fees_config
            },
            'student_list': {
                'name': 'Student List',
                'description': 'Generate list of all students with contact information.',
                'config': self.setup_class_filter_config
            },
            'attendance_summary': {
                'name': 'Attendance Summary',
                'description': 'Generate attendance summary report for a date range.',
                'config': self.setup_attendance_config
            },
            'student_attendance': {
                'name': 'Individual Student Attendance',
                'description': 'Generate attendance report for a specific student.',
                'config': self.setup_student_attendance_config
            },
            'inventory_list': {
                'name': 'Inventory List',
                'description': 'Generate complete inventory list with quantities and values.',
                'config': self.setup_category_filter_config
            },
            'low_stock': {
                'name': 'Low Stock Report',
                'description': 'Generate report of items below minimum quantity.',
                'config': self.setup_simple_config
            },
            'inventory_valuation': {
                'name': 'Inventory Valuation',
                'description': 'Generate inventory valuation report by category.',
                'config': self.setup_simple_config
            },
            'class_list': {
                'name': 'Class List',
                'description': 'Generate list of classes with student counts.',
                'config': self.setup_simple_config
            },
            'teacher_assignments': {
                'name': 'Teacher Assignments',
                'description': 'Generate report of teacher assignments by class.',
                'config': self.setup_simple_config
            }
        }
        
        config = report_configs.get(report_id, {
            'name': 'Unknown Report',
            'description': 'Report configuration not available.',
            'config': self.setup_simple_config
        })
        
        # Update header and description
        self.config_header.config(text=f"{config['name']} - Configuration")
        self.config_desc.config(text=config['description'])
        
        # Clear previous configuration
        for widget in self.config_frame.winfo_children():
            widget.destroy()
        
        # Setup new configuration
        config['config']()
        
        # Show configuration frame
        self.config_frame.pack(fill='x', pady=(0, 20))
        
        # Enable action buttons
        self.preview_btn.state(['!disabled'])
        self.generate_pdf_btn.state(['!disabled'])
        self.generate_excel_btn.state(['!disabled'])
    
    def setup_date_range_config(self):
        """Setup date range configuration"""
        # Default dates
        today = date.today()
        start_date = date(today.year, today.month, 1)  # First day of current month
        end_date = today
        
        ttk.Label(self.config_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.start_date_var = tk.StringVar(value=start_date.strftime('%Y-%m-%d'))
        start_date_entry = ttk.Entry(self.config_frame, textvariable=self.start_date_var, width=15)
        start_date_entry.grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(self.config_frame, text="End Date (YYYY-MM-DD):").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.end_date_var = tk.StringVar(value=end_date.strftime('%Y-%m-%d'))
        end_date_entry = ttk.Entry(self.config_frame, textvariable=self.end_date_var, width=15)
        end_date_entry.grid(row=1, column=1, sticky='w', pady=5)
        
        # Quick date buttons
        button_frame = ttk.Frame(self.config_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(
            button_frame,
            text="This Week",
            command=lambda: self.set_date_range('week'),
            width=10
        ).pack(side='left', padx=2)
        
        ttk.Button(
            button_frame,
            text="This Month",
            command=lambda: self.set_date_range('month'),
            width=10
        ).pack(side='left', padx=2)
        
        ttk.Button(
            button_frame,
            text="This Term",
            command=lambda: self.set_date_range('term'),
            width=10
        ).pack(side='left', padx=2)
        
        ttk.Button(
            button_frame,
            text="This Year",
            command=lambda: self.set_date_range('year'),
            width=10
        ).pack(side='left', padx=2)
    
    def setup_term_config(self):
        """Setup term configuration"""
        ttk.Label(self.config_frame, text="Academic Year:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.year_var = tk.StringVar(value=config.Config.CURRENT_ACADEMIC_YEAR)
        year_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.year_var,
            values=['2023', '2024', '2025'],
            width=10,
            state='readonly'
        )
        year_combo.grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(self.config_frame, text="Term:").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.term_var = tk.StringVar(value=config.Config.CURRENT_TERM)
        term_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.term_var,
            values=['Term 1', 'Term 2', 'Term 3', 'Annual'],
            width=10,
            state='readonly'
        )
        term_combo.grid(row=1, column=1, sticky='w', pady=5)
    
    def setup_student_fees_config(self):
        """Setup student fees configuration"""
        # Class filter
        ttk.Label(self.config_frame, text="Filter by Class:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.class_filter_var = tk.StringVar(value="All")
        
        # Get class list
        try:
            query = "SELECT DISTINCT class FROM students WHERE is_active = 1 ORDER BY class"
            results = db.execute_query(query, fetch=True)
            classes = ['All'] + [r['class'] for r in results]
        except:
            classes = ['All']
        
        class_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.class_filter_var,
            values=classes,
            width=15,
            state='readonly'
        )
        class_combo.grid(row=0, column=1, sticky='w', pady=5)
        
        # Balance filter
        ttk.Label(self.config_frame, text="Show Students with Balance:").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.balance_filter_var = tk.StringVar(value="All")
        balance_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.balance_filter_var,
            values=['All', 'With Balance Only', 'Cleared Only'],
            width=15,
            state='readonly'
        )
        balance_combo.grid(row=1, column=1, sticky='w', pady=5)
        
        # Academic year
        ttk.Label(self.config_frame, text="Academic Year:").grid(row=2, column=0, sticky='e', padx=(0, 10), pady=5)
        self.fee_year_var = tk.StringVar(value=config.Config.CURRENT_ACADEMIC_YEAR)
        year_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.fee_year_var,
            values=['2023', '2024', '2025'],
            width=10,
            state='readonly'
        )
        year_combo.grid(row=2, column=1, sticky='w', pady=5)
    
    def setup_class_filter_config(self):
        """Setup class filter configuration"""
        ttk.Label(self.config_frame, text="Filter by Class:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.report_class_var = tk.StringVar(value="All")
        
        # Get class list
        try:
            query = "SELECT DISTINCT class FROM students WHERE is_active = 1 ORDER BY class"
            results = db.execute_query(query, fetch=True)
            classes = ['All'] + [r['class'] for r in results]
        except:
            classes = ['All']
        
        class_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.report_class_var,
            values=classes,
            width=15,
            state='readonly'
        )
        class_combo.grid(row=0, column=1, sticky='w', pady=5)
        
        # Status filter
        ttk.Label(self.config_frame, text="Student Status:").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.status_filter_var = tk.StringVar(value="Active")
        status_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.status_filter_var,
            values=['Active', 'Inactive', 'All'],
            width=10,
            state='readonly'
        )
        status_combo.grid(row=1, column=1, sticky='w', pady=5)
    
    def setup_attendance_config(self):
        """Setup attendance report configuration"""
        # Date range
        today = date.today()
        start_date = date(today.year, today.month, 1)
        
        ttk.Label(self.config_frame, text="Start Date (YYYY-MM-DD):").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.att_start_date_var = tk.StringVar(value=start_date.strftime('%Y-%m-%d'))
        ttk.Entry(self.config_frame, textvariable=self.att_start_date_var, width=15).grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(self.config_frame, text="End Date (YYYY-MM-DD):").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.att_end_date_var = tk.StringVar(value=today.strftime('%Y-%m-%d'))
        ttk.Entry(self.config_frame, textvariable=self.att_end_date_var, width=15).grid(row=1, column=1, sticky='w', pady=5)
        
        # Class filter
        ttk.Label(self.config_frame, text="Filter by Class:").grid(row=2, column=0, sticky='e', padx=(0, 10), pady=5)
        self.att_class_var = tk.StringVar(value="All")
        
        try:
            query = "SELECT DISTINCT class FROM students WHERE is_active = 1 ORDER BY class"
            results = db.execute_query(query, fetch=True)
            classes = ['All'] + [r['class'] for r in results]
        except:
            classes = ['All']
        
        class_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.att_class_var,
            values=classes,
            width=15,
            state='readonly'
        )
        class_combo.grid(row=2, column=1, sticky='w', pady=5)
    
    def setup_student_attendance_config(self):
        """Setup individual student attendance configuration"""
        ttk.Label(self.config_frame, text="Select Student:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        
        self.selected_student_var = tk.StringVar(value="Click to select student")
        self.selected_student_id = None
        
        student_frame = ttk.Frame(self.config_frame)
        student_frame.grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(student_frame, textvariable=self.selected_student_var, width=30, anchor='w').pack(side='left')
        
        ttk.Button(
            student_frame,
            text="Select",
            command=self.select_student,
            width=8
        ).pack(side='left', padx=(5, 0))
        
        # Date range
        today = date.today()
        start_date = date(today.year, 1, 1)
        
        ttk.Label(self.config_frame, text="Start Date (YYYY-MM-DD):").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.student_start_date_var = tk.StringVar(value=start_date.strftime('%Y-%m-%d'))
        ttk.Entry(self.config_frame, textvariable=self.student_start_date_var, width=15).grid(row=1, column=1, sticky='w', pady=5)
        
        ttk.Label(self.config_frame, text="End Date (YYYY-MM-DD):").grid(row=2, column=0, sticky='e', padx=(0, 10), pady=5)
        self.student_end_date_var = tk.StringVar(value=today.strftime('%Y-%m-%d'))
        ttk.Entry(self.config_frame, textvariable=self.student_end_date_var, width=15).grid(row=2, column=1, sticky='w', pady=5)
    
    def setup_category_filter_config(self):
        """Setup category filter configuration"""
        ttk.Label(self.config_frame, text="Filter by Category:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.category_filter_var = tk.StringVar(value="All")
        
        try:
            query = "SELECT DISTINCT category FROM inventory_items ORDER BY category"
            results = db.execute_query(query, fetch=True)
            categories = ['All'] + [r['category'] for r in results if r['category']]
        except:
            categories = ['All']
        
        category_combo = ttk.Combobox(
            self.config_frame,
            textvariable=self.category_filter_var,
            values=categories,
            width=15,
            state='readonly'
        )
        category_combo.grid(row=0, column=1, sticky='w', pady=5)
    
    def setup_simple_config(self):
        """Setup simple configuration (no options)"""
        ttk.Label(self.config_frame, text="No additional configuration required.").grid(row=0, column=0, columnspan=2, pady=10)
    
    def set_date_range(self, period):
        """Set date range based on period"""
        today = date.today()
        
        if period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today
        elif period == 'month':
            start_date = date(today.year, today.month, 1)
            end_date = today
        elif period == 'term':
            # Get current term dates (simplified)
            start_date = date(today.year, 1, 1)
            end_date = today
        elif period == 'year':
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        else:
            return
        
        self.start_date_var.set(start_date.strftime('%Y-%m-%d'))
        self.end_date_var.set(end_date.strftime('%Y-%m-%d'))
    
    def select_student(self):
        """Open student selection dialog"""
        dialog = StudentSelectionDialog(self.frame)
        if dialog.show():
            self.selected_student_id = dialog.selected_student_id
            self.selected_student_var.set(dialog.selected_student_name)
    
    def get_report_parameters(self):
        """Get parameters for current report"""
        params = {}
        
        if self.current_report in ['fee_collection', 'expense']:
            params['start_date'] = self.start_date_var.get()
            params['end_date'] = self.end_date_var.get()
            
        elif self.current_report == 'financial_summary':
            params['academic_year'] = self.year_var.get()
            params['term'] = self.term_var.get()
            
        elif self.current_report == 'student_fees':
            params['class_filter'] = self.class_filter_var.get()
            params['balance_filter'] = self.balance_filter_var.get()
            params['academic_year'] = self.fee_year_var.get()
            
        elif self.current_report in ['student_list', 'attendance_summary']:
            params['class_filter'] = self.report_class_var.get()
            if hasattr(self, 'status_filter_var'):
                params['status_filter'] = self.status_filter_var.get()
            
        elif self.current_report == 'attendance_summary':
            params['start_date'] = self.att_start_date_var.get()
            params['end_date'] = self.att_end_date_var.get()
            params['class_filter'] = self.att_class_var.get()
            
        elif self.current_report == 'student_attendance':
            if not self.selected_student_id:
                raise ValueError("Please select a student")
            params['student_id'] = self.selected_student_id
            params['start_date'] = self.student_start_date_var.get()
            params['end_date'] = self.student_end_date_var.get()
            
        elif self.current_report == 'inventory_list':
            params['category_filter'] = self.category_filter_var.get()
        
        return params
    
    def validate_parameters(self, params):
        """Validate report parameters"""
        # Check date formats
        date_fields = ['start_date', 'end_date']
        for field in date_fields:
            if field in params:
                try:
                    datetime.strptime(params[field], '%Y-%m-%d')
                except ValueError:
                    return False, f"Invalid date format for {field.replace('_', ' ')}. Use YYYY-MM-DD"
        
        # Check date order
        if 'start_date' in params and 'end_date' in params:
            try:
                start = datetime.strptime(params['start_date'], '%Y-%m-%d').date()
                end = datetime.strptime(params['end_date'], '%Y-%m-%d').date()
                if start > end:
                    return False, "Start date cannot be after end date"
            except:
                pass
        
        return True, ""
    
    def preview_report(self):
        """Preview report in a window"""
        try:
            # Get parameters
            params = self.get_report_parameters()
            
            # Validate parameters
            is_valid, error_msg = self.validate_parameters(params)
            if not is_valid:
                messagebox.showerror("Validation Error", error_msg)
                return
            
            # Generate preview data
            data = self.generate_report_data(preview=True)
            
            if data:
                # Show preview window
                self.show_preview_window(data)
            else:
                messagebox.showinfo("No Data", "No data found for the selected criteria.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate preview: {str(e)}")
    
    def generate_report_data(self, preview=False):
        """Generate report data based on current selection"""
        try:
            params = self.get_report_parameters()
            
            if self.current_report == 'fee_collection':
                return self.get_fee_collection_data(params, preview)
            elif self.current_report == 'expense':
                return self.get_expense_data(params, preview)
            elif self.current_report == 'financial_summary':
                return self.get_financial_summary_data(params, preview)
            elif self.current_report == 'student_fees':
                return self.get_student_fees_data(params, preview)
            elif self.current_report == 'student_list':
                return self.get_student_list_data(params, preview)
            elif self.current_report == 'attendance_summary':
                return self.get_attendance_summary_data(params, preview)
            elif self.current_report == 'student_attendance':
                return self.get_student_attendance_data(params, preview)
            elif self.current_report == 'inventory_list':
                return self.get_inventory_list_data(params, preview)
            elif self.current_report == 'low_stock':
                return self.get_low_stock_data(params, preview)
            elif self.current_report == 'inventory_valuation':
                return self.get_inventory_valuation_data(params, preview)
            elif self.current_report == 'class_list':
                return self.get_class_list_data(params, preview)
            elif self.current_report == 'teacher_assignments':
                return self.get_teacher_assignments_data(params, preview)
            else:
                return None
                
        except Exception as e:
            print(f"Error generating report data: {e}")
            return None
    
    def get_fee_collection_data(self, params, preview=False):
        """Get fee collection data"""
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
        
        if preview:
            query += " LIMIT 50"
        
        return db.execute_query(query, (params['start_date'], params['end_date']), fetch=True)
    
    def get_expense_data(self, params, preview=False):
        """Get expense data"""
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
        
        if preview:
            query += " LIMIT 50"
        
        return db.execute_query(query, (params['start_date'], params['end_date']), fetch=True)
    
    def get_financial_summary_data(self, params, preview=False):
        """Get financial summary data"""
        # This would be more complex in reality
        summary = {}
        
        # Get fee totals
        fee_query = """
            SELECT 
                COALESCE(SUM(amount_paid), 0) as total_fees
            FROM student_fees
            WHERE YEAR(payment_date) = %s
        """
        fee_result = db.execute_query(fee_query, (params['academic_year'],), fetch=True)
        summary['total_fees'] = fee_result[0]['total_fees'] if fee_result else 0
        
        # Get expense totals
        expense_query = """
            SELECT 
                category,
                COALESCE(SUM(amount), 0) as total_amount
            FROM expenses
            WHERE YEAR(expense_date) = %s
            GROUP BY category
        """
        expense_result = db.execute_query(expense_query, (params['academic_year'],), fetch=True)
        summary['expenses'] = expense_result if expense_result else []
        
        # Get total expenses
        total_expense_query = """
            SELECT COALESCE(SUM(amount), 0) as total_expenses
            FROM expenses
            WHERE YEAR(expense_date) = %s
        """
        total_expense_result = db.execute_query(total_expense_query, (params['academic_year'],), fetch=True)
        summary['total_expenses'] = total_expense_result[0]['total_expenses'] if total_expense_result else 0
        
        summary['net_balance'] = summary['total_fees'] - summary['total_expenses']
        
        return summary
    
    def get_student_fees_data(self, params, preview=False):
        """Get student fees data"""
        query = """
            SELECT 
                s.student_id,
                s.student_code,
                CONCAT(s.first_name, ' ', s.last_name) as student_name,
                s.class,
                COALESCE(SUM(ft.amount), 0) as total_due,
                COALESCE(SUM(sf.amount_paid), 0) as total_paid,
                COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) as balance
            FROM students s
            CROSS JOIN fee_types ft
            LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
            WHERE s.is_active = 1 
                AND ft.academic_year = %s
        """
        
        conditions = []
        values = [params['academic_year']]
        
        # Add class filter
        if params['class_filter'] != 'All':
            conditions.append("s.class = %s")
            values.append(params['class_filter'])
        
        # Add balance filter
        if params['balance_filter'] == 'With Balance Only':
            conditions.append("COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) > 0")
        elif params['balance_filter'] == 'Cleared Only':
            conditions.append("COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) <= 0")
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += """
            GROUP BY s.student_id, s.student_code, s.first_name, s.last_name, s.class
            ORDER BY balance DESC, s.class, s.last_name
        """
        
        if preview:
            query += " LIMIT 50"
        
        return db.execute_query(query, values, fetch=True)
    
    def get_student_list_data(self, params, preview=False):
        """Get student list data"""
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
        
        # Add status filter
        if params.get('status_filter') == 'Active':
            conditions.append("s.is_active = 1")
        elif params.get('status_filter') == 'Inactive':
            conditions.append("s.is_active = 0")
        
        # Add class filter
        if params['class_filter'] != 'All':
            conditions.append("s.class = %s")
            values.append(params['class_filter'])
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " ORDER BY s.class, s.last_name, s.first_name"
        
        if preview:
            query += " LIMIT 50"
        
        return db.execute_query(query, values, fetch=True)
    
    def get_attendance_summary_data(self, params, preview=False):
        """Get attendance summary data"""
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
        
        values = [params['start_date'], params['end_date']]
        
        if params['class_filter'] != 'All':
            query += " AND s.class = %s"
            values.append(params['class_filter'])
        
        query += """
            GROUP BY a.attendance_date
            ORDER BY a.attendance_date DESC
        """
        
        if preview:
            query += " LIMIT 30"
        
        return db.execute_query(query, values, fetch=True)
    
    def get_student_attendance_data(self, params, preview=False):
        """Get individual student attendance data"""
        # Get student info
        student_query = """
            SELECT 
                student_code,
                CONCAT(first_name, ' ', last_name) as student_name,
                class
            FROM students
            WHERE student_id = %s
        """
        student_info = db.execute_query(student_query, (params['student_id'],), fetch=True)
        
        if not student_info:
            return None
        
        # Get attendance records
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
        
        attendance_data = db.execute_query(attendance_query, 
                                         (params['student_id'], params['start_date'], params['end_date']), 
                                         fetch=True)
        
        if preview and attendance_data:
            attendance_data = attendance_data[:30]
        
        return {
            'student_info': student_info[0],
            'attendance_data': attendance_data
        }
    
    def get_inventory_list_data(self, params, preview=False):
        """Get inventory list data"""
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
        
        if params['category_filter'] != 'All':
            conditions.append("category = %s")
            values.append(params['category_filter'])
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " ORDER BY category, item_name"
        
        if preview:
            query += " LIMIT 50"
        
        return db.execute_query(query, values, fetch=True)
    
    def get_low_stock_data(self, params, preview=False):
        """Get low stock data"""
        query = """
            SELECT 
                item_code,
                item_name,
                category,
                quantity,
                min_quantity,
                unit_price,
                total_value,
                (min_quantity - quantity) as reorder_quantity
            FROM inventory_items
            WHERE quantity < min_quantity
            ORDER BY (min_quantity - quantity) DESC
        """
        
        if preview:
            query += " LIMIT 50"
        
        return db.execute_query(query, fetch=True)
    
    def get_inventory_valuation_data(self, params, preview=False):
        """Get inventory valuation data"""
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
        
        return db.execute_query(query, fetch=True)
    
    def get_class_list_data(self, params, preview=False):
        """Get class list data"""
        query = """
            SELECT 
                class_name,
                COUNT(*) as student_count,
                MIN(enrollment_date) as oldest_enrollment,
                MAX(enrollment_date) as latest_enrollment
            FROM students
            WHERE is_active = 1
            GROUP BY class_name
            ORDER BY class_name
        """
        
        return db.execute_query(query, fetch=True)
    
    def get_teacher_assignments_data(self, params, preview=False):
        """Get teacher assignments data"""
        query = """
            SELECT 
                t.teacher_code,
                CONCAT(t.first_name, ' ', t.last_name) as teacher_name,
                t.subject_specialization,
                c.class_name,
                c.room_number,
                COUNT(sc.student_id) as student_count
            FROM teachers t
            JOIN classes c ON t.teacher_id = c.teacher_id
            LEFT JOIN student_classes sc ON c.class_id = sc.class_id
            WHERE t.is_active = 1
            GROUP BY t.teacher_id, t.teacher_code, t.first_name, t.last_name, 
                     t.subject_specialization, c.class_name, c.room_number
            ORDER BY t.last_name, t.first_name
        """
        
        return db.execute_query(query, fetch=True)
    
    def show_preview_window(self, data):
        """Show preview window with report data"""
        preview_window = tk.Toplevel(self.frame)
        preview_window.title(f"Report Preview - {self.current_report.replace('_', ' ').title()}")
        preview_window.geometry("900x600")
        
        # Header
        header_frame = ttk.Frame(preview_window, padding="10")
        header_frame.pack(fill='x')
        
        ttk.Label(
            header_frame, 
            text="Report Preview",
            style='Header.TLabel'
        ).pack(side='left')
        
        ttk.Label(
            header_frame,
            text=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ).pack(side='right')
        
        # Create text widget for preview
        text_frame = ttk.Frame(preview_window)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap='word')
        text_widget.pack(side='left', fill='both', expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_widget, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget['yscrollcommand'] = scrollbar.set
        
        # Format and insert data
        preview_text = self.format_preview_text(data)
        text_widget.insert('1.0', preview_text)
        text_widget.config(state='disabled')
        
        # Action buttons
        button_frame = ttk.Frame(preview_window, padding="10")
        button_frame.pack(fill='x', side='bottom')
        
        ttk.Button(
            button_frame,
            text="Close",
            command=preview_window.destroy
        ).pack(side='right', padx=(5, 0))
        
        ttk.Button(
            button_frame,
            text="Print",
            command=lambda: self.print_preview(preview_text)
        ).pack(side='right', padx=5)
        
        ttk.Button(
            button_frame,
            text="Copy to Clipboard",
            command=lambda: self.copy_to_clipboard(preview_text)
        ).pack(side='right', padx=5)
    
    def format_preview_text(self, data):
        """Format data for preview display"""
        if not data:
            return "No data available for the selected criteria."
        
        if isinstance(data, dict):
            # Handle summary reports
            return self.format_summary_data(data)
        elif isinstance(data, list):
            # Handle list reports
            return self.format_list_data(data)
        else:
            return str(data)
    
    def format_summary_data(self, data):
        """Format summary data for preview"""
        text = "=" * 60 + "\n"
        text += "REPORT SUMMARY\n"
        text += "=" * 60 + "\n\n"
        
        for key, value in data.items():
            if isinstance(value, list):
                text += f"{key.replace('_', ' ').title()}:\n"
                for item in value:
                    if isinstance(item, dict):
                        for subkey, subvalue in item.items():
                            text += f"  {subkey}: {subvalue}\n"
                    else:
                        text += f"  {item}\n"
                text += "\n"
            else:
                text += f"{key.replace('_', ' ').title()}: {value}\n"
        
        return text
    
    def format_list_data(self, data):
        """Format list data for preview"""
        if not data:
            return "No records found."
        
        # Get column names
        columns = list(data[0].keys())
        
        # Calculate column widths
        col_widths = {}
        for col in columns:
            max_len = len(str(col))
            for row in data:
                max_len = max(max_len, len(str(row.get(col, ''))))
            col_widths[col] = min(max_len, 30)
        
        # Create header
        text = ""
        for col in columns:
            text += f"{col:<{col_widths[col]}}  "
        text += "\n" + "-" * (sum(col_widths.values()) + len(columns) * 2) + "\n"
        
        # Add data rows
        for row in data:
            for col in columns:
                value = str(row.get(col, ''))
                if len(value) > 30:
                    value = value[:27] + "..."
                text += f"{value:<{col_widths[col]}}  "
            text += "\n"
        
        # Add summary
        text += "\n" + "=" * 60 + "\n"
        text += f"Total Records: {len(data)}\n"
        text += "=" * 60
        
        return text
    
    def print_preview(self, text):
        """Print preview text"""
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"report_{self.current_report}_{date.today()}.txt"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                messagebox.showinfo("Success", f"Report saved to:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {str(e)}")
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.frame.clipboard_clear()
        self.frame.clipboard_append(text)
        self.status_label.config(text="Copied to clipboard")
    
    def generate_pdf(self):
        """Generate PDF report"""
        try:
            # Get parameters
            params = self.get_report_parameters()
            
            # Validate parameters
            is_valid, error_msg = self.validate_parameters(params)
            if not is_valid:
                messagebox.showerror("Validation Error", error_msg)
                return
            
            # Ask for filename
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=f"{self.current_report}_{date.today()}.pdf"
            )
            
            if not filename:
                return
            
            # Generate report based on type
            if self.current_report == 'fee_collection':
                generate_fee_collection_report(
                    filename,
                    start_date=params['start_date'],
                    end_date=params['end_date']
                )
            elif self.current_report == 'expense':
                generate_expense_report(
                    filename,
                    start_date=params['start_date'],
                    end_date=params['end_date']
                )
            elif self.current_report == 'financial_summary':
                generate_financial_summary_report(
                    filename,
                    academic_year=params['academic_year'],
                    term=params['term']
                )
            elif self.current_report == 'student_fees':
                generate_student_fees_report(
                    filename,
                    class_filter=params['class_filter'],
                    balance_filter=params['balance_filter'],
                    academic_year=params['academic_year']
                )
            elif self.current_report == 'student_list':
                generate_student_list_report(
                    filename,
                    class_filter=params['class_filter'],
                    status_filter=params.get('status_filter', 'Active')
                )
            elif self.current_report == 'attendance_summary':
                generate_attendance_summary_report(
                    filename,
                    start_date=params['start_date'],
                    end_date=params['end_date'],
                    class_filter=params['class_filter']
                )
            elif self.current_report == 'student_attendance':
                generate_student_attendance_report(
                    filename,
                    student_id=params['student_id'],
                    start_date=params['start_date'],
                    end_date=params['end_date']
                )
            elif self.current_report == 'inventory_list':
                generate_inventory_list_report(
                    filename,
                    category_filter=params['category_filter']
                )
            elif self.current_report == 'low_stock':
                generate_low_stock_report(filename)
            elif self.current_report == 'inventory_valuation':
                generate_inventory_valuation_report(filename)
            else:
                messagebox.showinfo("Info", f"PDF generation for {self.current_report} is not yet implemented.")
                return
            
            # Show success message
            self.status_label.config(text=f"PDF generated: {filename}")
            messagebox.showinfo("Success", f"PDF report generated:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {str(e)}")
    
    def generate_excel(self):
        """Generate Excel report"""
        try:
            # Get parameters
            params = self.get_report_parameters()
            
            # Validate parameters
            is_valid, error_msg = self.validate_parameters(params)
            if not is_valid:
                messagebox.showerror("Validation Error", error_msg)
                return
            
            # Get data
            data = self.generate_report_data(preview=False)
            
            if not data:
                messagebox.showinfo("No Data", "No data found for the selected criteria.")
                return
            
            # Ask for filename
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                initialfile=f"{self.current_report}_{date.today()}.xlsx"
            )
            
            if not filename:
                return
            
            # Generate Excel file
            import pandas as pd
            
            if isinstance(data, list):
                # List data
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                # Summary data - create multiple sheets
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    for key, value in data.items():
                        if isinstance(value, list):
                            pd.DataFrame(value).to_excel(writer, sheet_name=key[:31], index=False)
                        else:
                            pd.DataFrame({key: [value]}).to_excel(writer, sheet_name='Summary', index=False)
            else:
                pd.DataFrame([{'Data': str(data)}]).to_excel(filename, index=False)
            
            if not isinstance(data, dict):
                # For simple data, just write one sheet
                df.to_excel(filename, index=False)
            
            # Show success message
            self.status_label.config(text=f"Excel generated: {filename}")
            messagebox.showinfo("Success", f"Excel report generated:\n{filename}")
            
        except ImportError:
            messagebox.showerror("Error", "Pandas library is required for Excel export. Install with: pip install pandas openpyxl")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate Excel: {str(e)}")
    
    def refresh_data(self):
        """Public method to refresh data (called from main window)"""
        # Update status
        self.status_label.config(text="Ready")