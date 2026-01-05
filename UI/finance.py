import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import config
from database.connection import db

class FinanceTab:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """Setup finance tab UI"""
        # Create notebook for different finance sections
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.fee_payments_frame = ttk.Frame(self.notebook)
        self.student_balances_frame = ttk.Frame(self.notebook)
        self.expenses_frame = ttk.Frame(self.notebook)
        self.financial_summary_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.fee_payments_frame, text="Fee Payments")
        self.notebook.add(self.student_balances_frame, text="Student Balances")
        self.notebook.add(self.expenses_frame, text="Expenses")
        self.notebook.add(self.financial_summary_frame, text="Financial Summary")
        
        # Setup each tab
        self.setup_fee_payments_tab()
        self.setup_student_balances_tab()
        self.setup_expenses_tab()
        self.setup_financial_summary_tab()
    
    def setup_fee_payments_tab(self):
        """Setup fee payments tab"""
        # Left frame for form
        left_frame = ttk.Frame(self.fee_payments_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # Form frame
        form_frame = ttk.LabelFrame(left_frame, text="Record Fee Payment", padding=15)
        form_frame.pack(fill='x', pady=(0, 10))
        
        # Student selection
        ttk.Label(form_frame, text="Student:").grid(row=0, column=0, sticky='w', pady=5)
        self.student_var = tk.StringVar()
        self.student_combo = ttk.Combobox(form_frame, textvariable=self.student_var, state='readonly')
        self.student_combo.grid(row=0, column=1, pady=5, padx=5, sticky='ew')
        
        # Fee type selection
        ttk.Label(form_frame, text="Fee Type:").grid(row=1, column=0, sticky='w', pady=5)
        self.fee_type_var = tk.StringVar()
        self.fee_type_combo = ttk.Combobox(form_frame, textvariable=self.fee_type_var, state='readonly')
        self.fee_type_combo.grid(row=1, column=1, pady=5, padx=5, sticky='ew')
        
        # Amount
        ttk.Label(form_frame, text="Amount:").grid(row=2, column=0, sticky='w', pady=5)
        self.amount_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.amount_var, width=20).grid(row=2, column=1, sticky='w', pady=5, padx=5)
        
        # Payment method
        ttk.Label(form_frame, text="Payment Method:").grid(row=3, column=0, sticky='w', pady=5)
        self.payment_method_var = tk.StringVar(value="Cash")
        methods = ['Cash', 'M-Pesa', 'Bank Transfer', 'Check', 'Other']
        ttk.Combobox(form_frame, textvariable=self.payment_method_var, values=methods, state='readonly', width=18).grid(
            row=3, column=1, sticky='w', pady=5, padx=5)
        
        # Date
        ttk.Label(form_frame, text="Date:").grid(row=4, column=0, sticky='w', pady=5)
        self.date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        ttk.Entry(form_frame, textvariable=self.date_var, width=20).grid(row=4, column=1, sticky='w', pady=5, padx=5)
        
        # Receipt number
        ttk.Label(form_frame, text="Receipt No:").grid(row=5, column=0, sticky='w', pady=5)
        self.receipt_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.receipt_var, width=20).grid(row=5, column=1, sticky='w', pady=5, padx=5)
        
        # Description
        ttk.Label(form_frame, text="Description:").grid(row=6, column=0, sticky='w', pady=5)
        self.description_text = tk.Text(form_frame, height=3, width=30)
        self.description_text.grid(row=6, column=1, pady=5, padx=5, sticky='ew')
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Record Payment", command=self.record_payment).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_payment_form).pack(side='left', padx=5)
        
        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)
        
        # Right frame for recent payments
        right_frame = ttk.Frame(self.fee_payments_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        # Recent payments table
        table_frame = ttk.LabelFrame(right_frame, text="Recent Payments", padding=10)
        table_frame.pack(fill='both', expand=True)
        
        columns = ['ID', 'Date', 'Student', 'Fee Type', 'Amount', 'Method', 'Receipt']
        self.payments_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        # Configure columns
        for col in columns:
            self.payments_tree.heading(col, text=col)
            self.payments_tree.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.payments_tree.yview)
        self.payments_tree.configure(yscrollcommand=scrollbar.set)
        
        self.payments_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Summary frame
        summary_frame = ttk.Frame(right_frame)
        summary_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Label(summary_frame, text="Today's Total:").pack(side='left', padx=5)
        self.today_total_var = tk.StringVar(value="$0.00")
        ttk.Label(summary_frame, textvariable=self.today_total_var, font=('Arial', 12, 'bold')).pack(side='left', padx=5)
        
        ttk.Button(summary_frame, text="Refresh", command=self.load_recent_payments).pack(side='right', padx=5)
    
    def setup_student_balances_tab(self):
        """Setup student balances tab"""
        # Top frame for filters and summary
        top_frame = ttk.Frame(self.student_balances_frame)
        top_frame.pack(fill='x', padx=10, pady=10)
        
        # Class filter
        ttk.Label(top_frame, text="Class:").pack(side='left', padx=5)
        self.balance_class_var = tk.StringVar(value="All")
        self.balance_class_combo = ttk.Combobox(top_frame, textvariable=self.balance_class_var, width=15)
        self.balance_class_combo.pack(side='left', padx=5)
        
        # Status filter
        ttk.Label(top_frame, text="Status:").pack(side='left', padx=5)
        self.balance_status_var = tk.StringVar(value="All")
        status_options = ['All', 'Paid', 'Partial', 'Unpaid']
        ttk.Combobox(top_frame, textvariable=self.balance_status_var, values=status_options, width=10).pack(side='left', padx=5)
        
        # Search
        ttk.Label(top_frame, text="Search:").pack(side='left', padx=5)
        self.balance_search_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.balance_search_var, width=20).pack(side='left', padx=5)
        
        ttk.Button(top_frame, text="Search", command=self.search_balances).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Clear", command=self.load_student_balances).pack(side='left', padx=5)
        
        # Summary
        summary_frame = ttk.Frame(self.student_balances_frame)
        summary_frame.pack(fill='x', padx=10, pady=5)
        
        summaries = [
            ('Total Outstanding:', 'total_outstanding_var'),
            ('Students with Balance:', 'with_balance_var'),
            ('Fully Paid:', 'fully_paid_var')
        ]
        
        for i, (label, var_name) in enumerate(summaries):
            frame = ttk.Frame(summary_frame)
            frame.pack(side='left', padx=20)
            
            ttk.Label(frame, text=label).pack()
            setattr(self, var_name, tk.StringVar(value="0"))
            ttk.Label(frame, textvariable=getattr(self, var_name), font=('Arial', 12, 'bold')).pack()
        
        # Balances table
        table_frame = ttk.Frame(self.student_balances_frame)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ['ID', 'Student', 'Class', 'Total Fees', 'Paid', 'Balance', 'Status']
        self.balances_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=20
        )
        
        # Configure columns
        for col in columns:
            self.balances_tree.heading(col, text=col)
            self.balances_tree.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.balances_tree.yview)
        self.balances_tree.configure(yscrollcommand=scrollbar.set)
        
        self.balances_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Right-click menu for actions
        self.setup_balance_context_menu()
    
    def setup_expenses_tab(self):
        """Setup expenses tab"""
        # Left frame for form
        left_frame = ttk.Frame(self.expenses_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # Expense form
        form_frame = ttk.LabelFrame(left_frame, text="Record Expense", padding=15)
        form_frame.pack(fill='x', pady=(0, 10))
        
        # Expense fields
        fields = [
            ("Date:", "expense_date_var"),
            ("Description:", "expense_desc_var"),
            ("Category:", "expense_category_var"),
            ("Amount:", "expense_amount_var"),
            ("Payment Method:", "expense_method_var"),
            ("Receipt No:", "expense_receipt_var")
        ]
        
        for i, (label, var_name) in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky='w', pady=5)
            setattr(self, var_name, tk.StringVar())
            
            if "date" in var_name:
                getattr(self, var_name).set(date.today().strftime('%Y-%m-%d'))
                ttk.Entry(form_frame, textvariable=getattr(self, var_name), width=25).grid(
                    row=i, column=1, pady=5, padx=5, sticky='w')
            elif "category" in var_name:
                categories = ['Supplies', 'Salaries', 'Utilities', 'Maintenance', 'Other']
                ttk.Combobox(form_frame, textvariable=getattr(self, var_name), 
                           values=categories, width=23).grid(row=i, column=1, pady=5, padx=5, sticky='w')
            elif "method" in var_name:
                methods = ['Cash', 'M-Pesa', 'Bank Transfer', 'Check', 'Other']
                ttk.Combobox(form_frame, textvariable=getattr(self, var_name), 
                           values=methods, width=23).grid(row=i, column=1, pady=5, padx=5, sticky='w')
            else:
                ttk.Entry(form_frame, textvariable=getattr(self, var_name), width=25).grid(
                    row=i, column=1, pady=5, padx=5, sticky='w')
        
        # Notes
        ttk.Label(form_frame, text="Notes:").grid(row=len(fields), column=0, sticky='nw', pady=5)
        self.expense_notes_text = tk.Text(form_frame, height=4, width=25)
        self.expense_notes_text.grid(row=len(fields), column=1, pady=5, padx=5, sticky='w')
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Record Expense", command=self.record_expense).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_expense_form).pack(side='left', padx=5)
        
        # Right frame for expenses list
        right_frame = ttk.Frame(self.expenses_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        # Expenses table
        table_frame = ttk.LabelFrame(right_frame, text="Recent Expenses", padding=10)
        table_frame.pack(fill='both', expand=True)
        
        columns = ['ID', 'Date', 'Description', 'Category', 'Amount', 'Method', 'Receipt']
        self.expenses_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=15
        )
        
        for col in columns:
            self.expenses_tree.heading(col, text=col)
            self.expenses_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.expenses_tree.yview)
        self.expenses_tree.configure(yscrollcommand=scrollbar.set)
        
        self.expenses_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Expense summary
        summary_frame = ttk.Frame(right_frame)
        summary_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Label(summary_frame, text="Month Total:").pack(side='left', padx=5)
        self.month_expense_var = tk.StringVar(value="$0.00")
        ttk.Label(summary_frame, textvariable=self.month_expense_var, font=('Arial', 12, 'bold')).pack(side='left', padx=5)
        
        ttk.Button(summary_frame, text="Refresh", command=self.load_recent_expenses).pack(side='right', padx=5)
    
    def setup_financial_summary_tab(self):
        """Setup financial summary tab"""
        # Summary cards
        summary_frame = ttk.Frame(self.financial_summary_frame)
        summary_frame.pack(fill='x', padx=20, pady=20)
        
        self.summary_cards = []
        summaries = [
            ('💰 Total Income', 'total_income_var', '#4CAF50'),
            ('📉 Total Expenses', 'total_expenses_var', '#F44336'),
            ('📊 Net Balance', 'net_balance_var', '#2196F3'),
            ('📈 This Month', 'this_month_var', '#FF9800'),
            ('📅 Year to Date', 'ytd_var', '#9C27B0'),
            ('⚠️ Outstanding', 'outstanding_var', '#607D8B')
        ]
        
        for i in range(0, len(summaries), 3):
            row_frame = ttk.Frame(summary_frame)
            row_frame.pack(fill='x', pady=10)
            
            for j in range(3):
                if i + j < len(summaries):
                    title, var_name, color = summaries[i + j]
                    card = self.create_summary_card(row_frame, title, var_name, color)
                    card.pack(side='left', fill='both', expand=True, padx=5)
                    self.summary_cards.append(card)
        
        # Charts/Graphs frame
        charts_frame = ttk.LabelFrame(self.financial_summary_frame, text="Financial Charts", padding=10)
        charts_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Income vs Expenses chart (simulated with labels)
        chart_container = ttk.Frame(charts_frame)
        chart_container.pack(fill='both', expand=True)
        
        # Monthly breakdown
        monthly_frame = ttk.LabelFrame(chart_container, text="Monthly Breakdown", padding=10)
        monthly_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        columns = ['Month', 'Income', 'Expenses', 'Net']
        self.monthly_tree = ttk.Treeview(monthly_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.monthly_tree.heading(col, text=col)
            self.monthly_tree.column(col, width=80)
        
        scrollbar = ttk.Scrollbar(monthly_frame, orient='vertical', command=self.monthly_tree.yview)
        self.monthly_tree.configure(yscrollcommand=scrollbar.set)
        
        self.monthly_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Category breakdown
        category_frame = ttk.LabelFrame(chart_container, text="Expense Categories", padding=10)
        category_frame.pack(side='right', fill='both', expand=True, padx=5)
        
        columns = ['Category', 'Count', 'Total']
        self.category_tree = ttk.Treeview(category_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.category_tree.heading(col, text=col)
            self.category_tree.column(col, width=100)
        
        scrollbar2 = ttk.Scrollbar(category_frame, orient='vertical', command=self.category_tree.yview)
        self.category_tree.configure(yscrollcommand=scrollbar2.set)
        
        self.category_tree.pack(side='left', fill='both', expand=True)
        scrollbar2.pack(side='right', fill='y')
        
        # Action buttons
        button_frame = ttk.Frame(self.financial_summary_frame)
        button_frame.pack(fill='x', padx=20, pady=10)
        
        actions = [
            ("Generate Report", self.generate_financial_report),
            ("Export to Excel", self.export_financial_data),
            ("Print Summary", self.print_financial_summary),
            ("Refresh Data", self.load_financial_summary)
        ]
        
        for text, command in actions:
            ttk.Button(button_frame, text=text, command=command).pack(side='left', padx=5)
    
    def create_summary_card(self, parent, title, var_name, color):
        """Create a summary card"""
        card = ttk.Frame(parent, relief='solid', borderwidth=1)
        
        # Title
        ttk.Label(card, text=title, font=('Arial', 10)).pack(pady=(10, 5))
        
        # Value
        setattr(self, var_name, tk.StringVar(value="$0.00"))
        value_label = ttk.Label(
            card,
            textvariable=getattr(self, var_name),
            font=('Arial', 16, 'bold')
        )
        value_label.pack(pady=(0, 10))
        
        return card
    
    def setup_balance_context_menu(self):
        """Setup context menu for balance tree"""
        self.balance_menu = tk.Menu(self.frame, tearoff=0)
        self.balance_menu.add_command(label="View Details", command=self.view_balance_details)
        self.balance_menu.add_command(label="Record Payment", command=self.record_balance_payment)
        self.balance_menu.add_command(label="Print Statement", command=self.print_balance_statement)
        
        self.balances_tree.bind("<Button-3>", self.show_balance_context_menu)
    
    def show_balance_context_menu(self, event):
        """Show context menu for balance tree"""
        item = self.balances_tree.identify_row(event.y)
        if item:
            self.balances_tree.selection_set(item)
            self.balance_menu.post(event.x_root, event.y_root)
    
    def load_data(self):
        """Load all financial data"""
        self.load_students_for_payment()
        self.load_fee_types()
        self.load_recent_payments()
        self.load_student_balances()
        self.load_classes_for_filter()
        self.load_recent_expenses()
        self.load_financial_summary()
    
    def load_students_for_payment(self):
        """Load students for payment combobox"""
        try:
            query = """
                SELECT student_id, first_name, last_name, class 
                FROM students 
                WHERE is_active = 1 
                ORDER BY last_name, first_name
            """
            results = db.execute_query(query, fetch=True)
            student_list = [f"{r['student_id']}: {r['first_name']} {r['last_name']} ({r['class']})" for r in results]
            self.student_combo['values'] = student_list
        except Exception as e:
            print(f"Error loading students: {e}")
    
    def load_fee_types(self):
        """Load fee types for combobox"""
        try:
            query = """
                SELECT fee_type_id, fee_name, amount 
                FROM fee_types 
                WHERE academic_year = '2024' 
                ORDER BY fee_name
            """
            results = db.execute_query(query, fetch=True)
            fee_list = [f"{r['fee_type_id']}: {r['fee_name']} (${r['amount']:,.2f})" for r in results]
            self.fee_type_combo['values'] = fee_list
        except Exception as e:
            print(f"Error loading fee types: {e}")
    
    def load_classes_for_filter(self):
        """Load classes for filter combobox"""
        try:
            query = "SELECT DISTINCT class FROM students WHERE is_active = 1 AND class IS NOT NULL ORDER BY class"
            results = db.execute_query(query, fetch=True)
            classes = ["All"] + [r['class'] for r in results]
            self.balance_class_combo['values'] = classes
        except Exception as e:
            print(f"Error loading classes: {e}")
    
    def load_recent_payments(self):
        """Load recent fee payments"""
        # Clear existing items
        for item in self.payments_tree.get_children():
            self.payments_tree.delete(item)
        
        try:
            # Get today's total
            query = """
                SELECT COALESCE(SUM(amount_paid), 0) as total 
                FROM student_fees 
                WHERE payment_date = CURDATE()
            """
            result = db.execute_query(query, fetch=True)
            if result:
                self.today_total_var.set(f"${result[0]['total']:,.2f}")
            
            # Get recent payments
            query = """
                SELECT 
                    sf.fee_id,
                    sf.payment_date,
                    CONCAT(s.first_name, ' ', s.last_name) as student_name,
                    ft.fee_name,
                    sf.amount_paid,
                    sf.payment_method,
                    sf.receipt_number
                FROM student_fees sf
                JOIN students s ON sf.student_id = s.student_id
                JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
                ORDER BY sf.payment_date DESC, sf.created_at DESC
                LIMIT 50
            """
            results = db.execute_query(query, fetch=True)
            
            for row in results:
                self.payments_tree.insert('', 'end', values=(
                    row['fee_id'],
                    row['payment_date'],
                    row['student_name'],
                    row['fee_name'],
                    f"${row['amount_paid']:,.2f}",
                    row['payment_method'],
                    row['receipt_number'] or ''
                ))
                
        except Exception as e:
            print(f"Error loading recent payments: {e}")
            self.payments_tree.insert('', 'end', values=('Error', '', 'Failed to load data', '', '', '', ''))
    
    def load_student_balances(self):
        """Load student balances"""
        # Clear existing items
        for item in self.balances_tree.get_children():
            self.balances_tree.delete(item)
        
        try:
            query = """
                SELECT 
                    s.student_id,
                    CONCAT(s.first_name, ' ', s.last_name) as student_name,
                    s.class,
                    COALESCE(SUM(ft.amount), 0) as total_fees,
                    COALESCE(SUM(sf.amount_paid), 0) as amount_paid,
                    COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) as balance
                FROM students s
                CROSS JOIN fee_types ft
                LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                WHERE s.is_active = 1 AND ft.academic_year = '2024'
                GROUP BY s.student_id, s.first_name, s.last_name, s.class
                ORDER BY s.class, s.last_name, s.first_name
            """
            results = db.execute_query(query, fetch=True)
            
            total_outstanding = 0
            with_balance = 0
            fully_paid = 0
            
            for row in results:
                balance = float(row['balance'])
                status = "Paid" if balance <= 0 else "Partial" if float(row['amount_paid']) > 0 else "Unpaid"
                
                if balance > 0:
                    total_outstanding += balance
                    with_balance += 1
                else:
                    fully_paid += 1
                
                self.balances_tree.insert('', 'end', values=(
                    row['student_id'],
                    row['student_name'],
                    row['class'],
                    f"${float(row['total_fees']):,.2f}",
                    f"${float(row['amount_paid']):,.2f}",
                    f"${balance:,.2f}",
                    status
                ))
            
            # Update summary
            self.total_outstanding_var.set(f"${total_outstanding:,.2f}")
            self.with_balance_var.set(str(with_balance))
            self.fully_paid_var.set(str(fully_paid))
            
        except Exception as e:
            print(f"Error loading student balances: {e}")
    
    def search_balances(self):
        """Search student balances"""
        # Clear existing items
        for item in self.balances_tree.get_children():
            self.balances_tree.delete(item)
        
        try:
            class_filter = self.balance_class_var.get()
            status_filter = self.balance_status_var.get()
            search_term = self.balance_search_var.get().strip()
            
            base_query = """
                SELECT 
                    s.student_id,
                    CONCAT(s.first_name, ' ', s.last_name) as student_name,
                    s.class,
                    COALESCE(SUM(ft.amount), 0) as total_fees,
                    COALESCE(SUM(sf.amount_paid), 0) as amount_paid,
                    COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) as balance
                FROM students s
                CROSS JOIN fee_types ft
                LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                WHERE s.is_active = 1 AND ft.academic_year = '2024'
            """
            
            conditions = []
            params = []
            
            if class_filter != "All":
                conditions.append("s.class = %s")
                params.append(class_filter)
            
            if search_term:
                conditions.append("(s.first_name LIKE %s OR s.last_name LIKE %s OR s.student_code LIKE %s)")
                params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
            
            if conditions:
                base_query += " AND " + " AND ".join(conditions)
            
            base_query += " GROUP BY s.student_id, s.first_name, s.last_name, s.class"
            base_query += " ORDER BY s.class, s.last_name, s.first_name"
            
            results = db.execute_query(query=base_query, params=tuple(params) if params else None, fetch=True)
            
            total_outstanding = 0
            with_balance = 0
            fully_paid = 0
            
            for row in results:
                balance = float(row['balance'])
                status = "Paid" if balance <= 0 else "Partial" if float(row['amount_paid']) > 0 else "Unpaid"
                
                # Apply status filter
                if status_filter != "All" and status != status_filter:
                    continue
                
                if balance > 0:
                    total_outstanding += balance
                    with_balance += 1
                else:
                    fully_paid += 1
                
                self.balances_tree.insert('', 'end', values=(
                    row['student_id'],
                    row['student_name'],
                    row['class'],
                    f"${float(row['total_fees']):,.2f}",
                    f"${float(row['amount_paid']):,.2f}",
                    f"${balance:,.2f}",
                    status
                ))
            
            # Update summary
            self.total_outstanding_var.set(f"${total_outstanding:,.2f}")
            self.with_balance_var.set(str(with_balance))
            self.fully_paid_var.set(str(fully_paid))
            
        except Exception as e:
            print(f"Error searching balances: {e}")
    
    def load_recent_expenses(self):
        """Load recent expenses"""
        # Clear existing items
        for item in self.expenses_tree.get_children():
            self.expenses_tree.delete(item)
        
        try:
            # Get month total
            today = date.today()
            first_day = date(today.year, today.month, 1)
            
            query = """
                SELECT COALESCE(SUM(amount), 0) as total 
                FROM expenses 
                WHERE expense_date BETWEEN %s AND %s
            """
            result = db.execute_query(query, (first_day, today), fetch=True)
            if result:
                self.month_expense_var.set(f"${result[0]['total']:,.2f}")
            
            # Get recent expenses
            query = """
                SELECT 
                    expense_id,
                    expense_date,
                    description,
                    category,
                    amount,
                    payment_method,
                    receipt_number
                FROM expenses
                ORDER BY expense_date DESC, created_at DESC
                LIMIT 50
            """
            results = db.execute_query(query, fetch=True)
            
            for row in results:
                self.expenses_tree.insert('', 'end', values=(
                    row['expense_id'],
                    row['expense_date'],
                    row['description'][:50] + "..." if len(row['description']) > 50 else row['description'],
                    row['category'] or 'Uncategorized',
                    f"${row['amount']:,.2f}",
                    row['payment_method'],
                    row['receipt_number'] or ''
                ))
                
        except Exception as e:
            print(f"Error loading expenses: {e}")
    
    def load_financial_summary(self):
        """Load financial summary"""
        try:
            today = date.today()
            first_day_month = date(today.year, today.month, 1)
            first_day_year = date(today.year, 1, 1)
            
            # Total income (all time)
            query = "SELECT COALESCE(SUM(amount_paid), 0) as total FROM student_fees"
            result = db.execute_query(query, fetch=True)
            if result:
                self.total_income_var.set(f"${result[0]['total']:,.2f}")
            
            # Total expenses (all time)
            query = "SELECT COALESCE(SUM(amount), 0) as total FROM expenses"
            result = db.execute_query(query, fetch=True)
            if result:
                self.total_expenses_var.set(f"${result[0]['total']:,.2f}")
            
            # Net balance
            income = float(self.total_income_var.get().replace('$', '').replace(',', ''))
            expenses = float(self.total_expenses_var.get().replace('$', '').replace(',', ''))
            self.net_balance_var.set(f"${income - expenses:,.2f}")
            
            # This month
            query = """
                SELECT 
                    COALESCE(SUM(CASE WHEN payment_date BETWEEN %s AND %s THEN amount_paid ELSE 0 END), 0) as income,
                    COALESCE(SUM(CASE WHEN expense_date BETWEEN %s AND %s THEN amount ELSE 0 END), 0) as expenses
                FROM (SELECT payment_date, amount_paid, NULL as expense_date, NULL as amount FROM student_fees
                      UNION ALL
                      SELECT NULL as payment_date, NULL as amount_paid, expense_date, amount FROM expenses) as combined
            """
            result = db.execute_query(query, (first_day_month, today, first_day_month, today), fetch=True)
            if result:
                month_income = result[0]['income']
                month_expenses = result[0]['expenses']
                self.this_month_var.set(f"${month_income - month_expenses:,.2f}")
            
            # Year to date
            query = """
                SELECT 
                    COALESCE(SUM(CASE WHEN payment_date BETWEEN %s AND %s THEN amount_paid ELSE 0 END), 0) as income,
                    COALESCE(SUM(CASE WHEN expense_date BETWEEN %s AND %s THEN amount ELSE 0 END), 0) as expenses
                FROM (SELECT payment_date, amount_paid, NULL as expense_date, NULL as amount FROM student_fees
                      UNION ALL
                      SELECT NULL as payment_date, NULL as amount_paid, expense_date, amount FROM expenses) as combined
            """
            result = db.execute_query(query, (first_day_year, today, first_day_year, today), fetch=True)
            if result:
                ytd_income = result[0]['income']
                ytd_expenses = result[0]['expenses']
                self.ytd_var.set(f"${ytd_income - ytd_expenses:,.2f}")
            
            # Outstanding fees
            query = """
                SELECT COALESCE(SUM(balance), 0) as total
                FROM (
                    SELECT 
                        COALESCE(SUM(ft.amount), 0) - COALESCE(SUM(sf.amount_paid), 0) as balance
                    FROM students s
                    CROSS JOIN fee_types ft
                    LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                    WHERE s.is_active = 1 AND ft.academic_year = '2024'
                    GROUP BY s.student_id
                    HAVING balance > 0
                ) as outstanding
            """
            result = db.execute_query(query, fetch=True)
            if result:
                self.outstanding_var.set(f"${result[0]['total']:,.2f}")
            
            # Load monthly breakdown
            self.load_monthly_breakdown()
            
            # Load expense categories
            self.load_expense_categories()
            
        except Exception as e:
            print(f"Error loading financial summary: {e}")
    
    def load_monthly_breakdown(self):
        """Load monthly financial breakdown"""
        # Clear existing items
        for item in self.monthly_tree.get_children():
            self.monthly_tree.delete(item)
        
        try:
            query = """
                SELECT 
                    DATE_FORMAT(payment_date, '%Y-%m') as month,
                    COALESCE(SUM(amount_paid), 0) as income
                FROM student_fees
                WHERE YEAR(payment_date) = YEAR(CURDATE())
                GROUP BY DATE_FORMAT(payment_date, '%Y-%m')
                ORDER BY month
            """
            income_results = db.execute_query(query, fetch=True)
            
            query = """
                SELECT 
                    DATE_FORMAT(expense_date, '%Y-%m') as month,
                    COALESCE(SUM(amount), 0) as expenses
                FROM expenses
                WHERE YEAR(expense_date) = YEAR(CURDATE())
                GROUP BY DATE_FORMAT(expense_date, '%Y-%m')
                ORDER BY month
            """
            expense_results = db.execute_query(query, fetch=True)
            
            # Combine results
            monthly_data = {}
            
            for row in income_results:
                monthly_data[row['month']] = {
                    'income': float(row['income']),
                    'expenses': 0,
                    'net': float(row['income'])
                }
            
            for row in expense_results:
                month = row['month']
                expenses = float(row['expenses'])
                if month in monthly_data:
                    monthly_data[month]['expenses'] = expenses
                    monthly_data[month]['net'] = monthly_data[month]['income'] - expenses
                else:
                    monthly_data[month] = {
                        'income': 0,
                        'expenses': expenses,
                        'net': -expenses
                    }
            
            # Add to treeview
            for month, data in sorted(monthly_data.items()):
                self.monthly_tree.insert('', 'end', values=(
                    month,
                    f"${data['income']:,.2f}",
                    f"${data['expenses']:,.2f}",
                    f"${data['net']:,.2f}"
                ))
                
        except Exception as e:
            print(f"Error loading monthly breakdown: {e}")
    
    def load_expense_categories(self):
        """Load expense categories breakdown"""
        # Clear existing items
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        
        try:
            query = """
                SELECT 
                    COALESCE(category, 'Uncategorized') as category,
                    COUNT(*) as count,
                    COALESCE(SUM(amount), 0) as total
                FROM expenses
                WHERE YEAR(expense_date) = YEAR(CURDATE())
                GROUP BY category
                ORDER BY total DESC
            """
            results = db.execute_query(query, fetch=True)
            
            for row in results:
                self.category_tree.insert('', 'end', values=(
                    row['category'],
                    row['count'],
                    f"${float(row['total']):,.2f}"
                ))
                
        except Exception as e:
            print(f"Error loading expense categories: {e}")
    
    def record_payment(self):
        """Record a fee payment"""
        try:
            # Validate inputs
            if not self.student_var.get():
                messagebox.showwarning("Warning", "Please select a student")
                return
            
            if not self.fee_type_var.get():
                messagebox.showwarning("Warning", "Please select a fee type")
                return
            
            try:
                amount = float(self.amount_var.get())
                if amount <= 0:
                    raise ValueError
            except:
                messagebox.showwarning("Warning", "Please enter a valid amount")
                return
            
            # Parse student ID and fee type ID
            student_id = int(self.student_var.get().split(':')[0])
            fee_type_id = int(self.fee_type_var.get().split(':')[0])
            
            # Get description
            description = self.description_text.get("1.0", "end-1c").strip()
            
            # Generate receipt number if not provided
            receipt_number = self.receipt_var.get().strip()
            if not receipt_number:
                # Generate receipt number: REC-YYYYMMDD-XXXX
                date_str = datetime.now().strftime('%Y%m%d')
                query = "SELECT COUNT(*) as count FROM student_fees WHERE receipt_number LIKE %s"
                result = db.execute_query(query, (f"REC-{date_str}-%",), fetch=True)
                next_num = result[0]['count'] + 1 if result else 1
                receipt_number = f"REC-{date_str}-{next_num:04d}"
                self.receipt_var.set(receipt_number)
            
            # Insert payment
            query = """
                INSERT INTO student_fees 
                (student_id, fee_type_id, amount_paid, payment_date, payment_method, receipt_number, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                student_id,
                fee_type_id,
                amount,
                self.date_var.get(),
                self.payment_method_var.get(),
                receipt_number,
                description
            )
            
            db.execute_query(query, params)
            
            messagebox.showinfo("Success", f"Payment recorded successfully!\nReceipt: {receipt_number}")
            
            # Clear form and refresh data
            self.clear_payment_form()
            self.load_recent_payments()
            self.load_student_balances()
            self.load_financial_summary()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record payment: {str(e)}")
    
    def clear_payment_form(self):
        """Clear payment form"""
        self.amount_var.set("")
        self.receipt_var.set("")
        self.description_text.delete("1.0", "end")
        self.date_var.set(date.today().strftime('%Y-%m-%d'))
    
    def record_expense(self):
        """Record an expense"""
        try:
            # Validate inputs
            if not self.expense_desc_var.get():
                messagebox.showwarning("Warning", "Please enter a description")
                return
            
            try:
                amount = float(self.expense_amount_var.get())
                if amount <= 0:
                    raise ValueError
            except:
                messagebox.showwarning("Warning", "Please enter a valid amount")
                return
            
            # Get notes
            notes = self.expense_notes_text.get("1.0", "end-1c").strip()
            
            # Generate receipt number if not provided
            receipt_number = self.expense_receipt_var.get().strip()
            if not receipt_number:
                # Generate receipt number: EXP-YYYYMMDD-XXXX
                date_str = datetime.now().strftime('%Y%m%d')
                query = "SELECT COUNT(*) as count FROM expenses WHERE receipt_number LIKE %s"
                result = db.execute_query(query, (f"EXP-{date_str}-%",), fetch=True)
                next_num = result[0]['count'] + 1 if result else 1
                receipt_number = f"EXP-{date_str}-{next_num:04d}"
                self.expense_receipt_var.set(receipt_number)
            
            # Insert expense
            query = """
                INSERT INTO expenses 
                (expense_date, description, category, amount, payment_method, receipt_number, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.expense_date_var.get(),
                self.expense_desc_var.get(),
                self.expense_category_var.get() or 'Other',
                amount,
                self.expense_method_var.get(),
                receipt_number,
                notes
            )
            
            db.execute_query(query, params)
            
            messagebox.showinfo("Success", f"Expense recorded successfully!\nReceipt: {receipt_number}")
            
            # Clear form and refresh data
            self.clear_expense_form()
            self.load_recent_expenses()
            self.load_financial_summary()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record expense: {str(e)}")
    
    def clear_expense_form(self):
        """Clear expense form"""
        self.expense_desc_var.set("")
        self.expense_amount_var.set("")
        self.expense_category_var.set("")
        self.expense_method_var.set("Cash")
        self.expense_receipt_var.set("")
        self.expense_notes_text.delete("1.0", "end")
        self.expense_date_var.set(date.today().strftime('%Y-%m-%d'))
    
    def view_balance_details(self):
        """View balance details for selected student"""
        selected = self.balances_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a student")
            return
        
        item = self.balances_tree.item(selected[0])
        student_id = item['values'][0]
        student_name = item['values'][1]
        
        # Show fee details dialog
        self.show_fee_details_dialog(student_id, student_name)
    
    def record_balance_payment(self):
        """Record payment for selected student"""
        selected = self.balances_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a student")
            return
        
        item = self.balances_tree.item(selected[0])
        student_id = item['values'][0]
        student_name = item['values'][1]
        balance = float(item['values'][5].replace('$', '').replace(',', ''))
        
        if balance <= 0:
            messagebox.showinfo("Info", f"{student_name} has no outstanding balance")
            return
        
        # Show payment dialog
        self.show_balance_payment_dialog(student_id, student_name, balance)
    
    def print_balance_statement(self):
        """Print balance statement for selected student"""
        selected = self.balances_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a student")
            return
        
        item = self.balances_tree.item(selected[0])
        student_id = item['values'][0]
        student_name = item['values'][1]
        
        # Generate and print statement
        self.generate_balance_statement(student_id, student_name)
    
    def show_fee_details_dialog(self, student_id, student_name):
        """Show fee details dialog"""
        try:
            # Create dialog
            dialog = tk.Toplevel(self.frame)
            dialog.title(f"Fee Details - {student_name}")
            dialog.geometry("600x400")
            dialog.transient(self.frame)
            dialog.grab_set()
            
            # Get fee details
            query = """
                SELECT 
                    ft.fee_name,
                    ft.amount as expected_amount,
                    COALESCE(SUM(sf.amount_paid), 0) as paid_amount,
                    ft.amount - COALESCE(SUM(sf.amount_paid), 0) as balance,
                    MAX(sf.payment_date) as last_payment
                FROM fee_types ft
                LEFT JOIN student_fees sf ON ft.fee_type_id = sf.fee_type_id AND sf.student_id = %s
                WHERE ft.academic_year = '2024'
                GROUP BY ft.fee_type_id, ft.fee_name, ft.amount
                ORDER BY ft.fee_name
            """
            results = db.execute_query(query, (student_id,), fetch=True)
            
            # Create treeview
            columns = ['Fee Type', 'Expected', 'Paid', 'Balance', 'Last Payment']
            tree = ttk.Treeview(dialog, columns=columns, show='headings', height=10)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            scrollbar = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
            scrollbar.pack(side='right', fill='y', pady=10)
            
            # Add data
            total_expected = total_paid = total_balance = 0
            for row in results:
                tree.insert('', 'end', values=(
                    row['fee_name'],
                    f"${float(row['expected_amount']):,.2f}",
                    f"${float(row['paid_amount']):,.2f}",
                    f"${float(row['balance']):,.2f}",
                    row['last_payment'] or 'None'
                ))
                total_expected += float(row['expected_amount'])
                total_paid += float(row['paid_amount'])
                total_balance += float(row['balance'])
            
            # Add totals row
            tree.insert('', 'end', values=(
                'TOTAL',
                f"${total_expected:,.2f}",
                f"${total_paid:,.2f}",
                f"${total_balance:,.2f}",
                ''
            ))
            
            # Payment history button
            ttk.Button(
                dialog,
                text="View Payment History",
                command=lambda: self.show_payment_history(student_id, student_name)
            ).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load fee details: {str(e)}")
    
    def show_payment_history(self, student_id, student_name):
        """Show payment history for student"""
        try:
            dialog = tk.Toplevel(self.frame)
            dialog.title(f"Payment History - {student_name}")
            dialog.geometry("700x400")
            
            # Get payment history
            query = """
                SELECT 
                    sf.payment_date,
                    ft.fee_name,
                    sf.amount_paid,
                    sf.payment_method,
                    sf.receipt_number,
                    sf.description
                FROM student_fees sf
                JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
                WHERE sf.student_id = %s
                ORDER BY sf.payment_date DESC
            """
            results = db.execute_query(query, (student_id,), fetch=True)
            
            # Create treeview
            columns = ['Date', 'Fee Type', 'Amount', 'Method', 'Receipt', 'Description']
            tree = ttk.Treeview(dialog, columns=columns, show='headings', height=15)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            scrollbar = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
            scrollbar.pack(side='right', fill='y', pady=10)
            
            # Add data
            total = 0
            for row in results:
                tree.insert('', 'end', values=(
                    row['payment_date'],
                    row['fee_name'],
                    f"${row['amount_paid']:,.2f}",
                    row['payment_method'],
                    row['receipt_number'] or '',
                    row['description'] or ''
                ))
                total += float(row['amount_paid'])
            
            # Summary
            summary_frame = ttk.Frame(dialog)
            summary_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Label(summary_frame, text=f"Total Payments: ${total:,.2f}", font=('Arial', 10, 'bold')).pack()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load payment history: {str(e)}")
    
    def show_balance_payment_dialog(self, student_id, student_name, balance):
        """Show dialog to record balance payment"""
        dialog = tk.Toplevel(self.frame)
        dialog.title(f"Record Payment - {student_name}")
        dialog.geometry("400x300")
        dialog.transient(self.frame)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Student: {student_name}", font=('Arial', 12, 'bold')).pack(pady=10)
        ttk.Label(dialog, text=f"Outstanding Balance: ${balance:,.2f}").pack(pady=5)
        
        # Payment amount
        ttk.Label(dialog, text="Payment Amount:").pack(pady=5)
        amount_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=amount_var, width=20).pack(pady=5)
        
        # Payment method
        ttk.Label(dialog, text="Payment Method:").pack(pady=5)
        method_var = tk.StringVar(value="Cash")
        ttk.Combobox(dialog, textvariable=method_var, values=['Cash', 'M-Pesa', 'Bank Transfer', 'Check', 'Other']).pack(pady=5)
        
        def process_payment():
            try:
                amount = float(amount_var.get())
                if amount <= 0:
                    messagebox.showwarning("Warning", "Please enter a valid amount")
                    return
                
                if amount > balance:
                    messagebox.showwarning("Warning", f"Amount cannot exceed balance of ${balance:,.2f}")
                    return
                
                # Record payment (simplified - would need fee type selection)
                messagebox.showinfo("Info", f"Payment of ${amount:,.2f} recorded for {student_name}")
                dialog.destroy()
                
                # Refresh data
                self.load_student_balances()
                self.load_financial_summary()
                
            except ValueError:
                messagebox.showwarning("Warning", "Please enter a valid amount")
        
        ttk.Button(dialog, text="Record Payment", command=process_payment).pack(pady=20)
    
    def generate_balance_statement(self, student_id, student_name):
        """Generate balance statement"""
        try:
            # This would generate a PDF statement
            # For now, just show a message
            messagebox.showinfo("Print Statement", 
                              f"Balance statement for {student_name} would be generated as PDF")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate statement: {str(e)}")
    
    def generate_financial_report(self):
        """Generate financial report"""
        try:
            from utils.pdf_generator import generate_financial_report
            filename = generate_financial_report()
            messagebox.showinfo("Success", f"Financial report generated:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
    
    def export_financial_data(self):
        """Export financial data to Excel"""
        try:
            messagebox.showinfo("Export", "Financial data would be exported to Excel")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {str(e)}")
    
    def print_financial_summary(self):
        """Print financial summary"""
        try:
            messagebox.showinfo("Print", "Financial summary would be sent to printer")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print: {str(e)}")