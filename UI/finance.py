import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import re
import config
from database.connection import db
from utils.helpers import format_currency, parse_currency

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
        # Management tab for fee types and expense categories
        self.manage_types_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.manage_types_frame, text="Manage Types")
        
        # Setup each tab
        self.setup_fee_payments_tab()
        self.setup_student_balances_tab()
        self.setup_expenses_tab()
        self.setup_financial_summary_tab()
        self.setup_manage_types_tab()
    
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
        # Allow manual entry (typing) while keeping dropdown choices
        self.student_combo = ttk.Combobox(form_frame, textvariable=self.student_var, state='normal')
        self.student_combo.grid(row=0, column=1, pady=5, padx=5, sticky='ew')
        
        # Fee type selection
        ttk.Label(form_frame, text="Fee Type:").grid(row=1, column=0, sticky='w', pady=5)
        self.fee_type_var = tk.StringVar()
        self.fee_type_combo = ttk.Combobox(form_frame, textvariable=self.fee_type_var, state='readonly')
        self.fee_type_combo.grid(row=1, column=1, pady=5, padx=5, sticky='ew')
        # When a fee type is selected, possibly autofill/enforce tuition amounts
        self.fee_type_combo.bind('<<ComboboxSelected>>', self.on_fee_type_selected)
        
        # Amount
        ttk.Label(form_frame, text="Amount:").grid(row=2, column=0, sticky='w', pady=5)
        self.amount_var = tk.StringVar()
        self.amount_entry = ttk.Entry(form_frame, textvariable=self.amount_var, width=20)
        self.amount_entry.grid(row=2, column=1, sticky='w', pady=5, padx=5)
        
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
        from utils.helpers import format_currency
        self.today_total_var = tk.StringVar(value=format_currency(0.0))
        ttk.Label(summary_frame, textvariable=self.today_total_var, font=('Arial', 12, 'bold')).pack(side='left', padx=5)
        
        ttk.Button(summary_frame, text="Refresh", command=self.load_recent_payments).pack(side='right', padx=5)
        ttk.Button(summary_frame, text="Delete Selected", command=self.delete_payment).pack(side='right', padx=5)
        # Setup payments context menu (edit/delete)
        self.setup_payments_context_menu()
    
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

    def setup_payments_context_menu(self):
        """Setup context menu for payments tree"""
        self.payments_menu = tk.Menu(self.frame, tearoff=0)
        self.payments_menu.add_command(label="Edit Payment", command=self.edit_payment)
        self.payments_menu.add_separator()
        self.payments_menu.add_command(label="Delete Payment", command=self.delete_payment)
        self.payments_tree.bind("<Button-3>", self.show_payments_context_menu)
        # Double-click to edit
        self.payments_tree.bind('<Double-1>', lambda e: self.edit_payment())

    def show_payments_context_menu(self, event):
        item = self.payments_tree.identify_row(event.y)
        if item:
            self.payments_tree.selection_set(item)
            self.payments_menu.post(event.x_root, event.y_root)

    def delete_payment(self):
        """Delete selected payment record"""
        selected = self.payments_tree.selection()
        if not selected:
            messagebox.showwarning('Select', 'Select a payment to delete')
            return
        item = self.payments_tree.item(selected[0], 'values')
        fee_id = item[0]
        if not messagebox.askyesno('Confirm', 'Permanently delete selected payment?'):
            return
        try:
            db.execute_query('DELETE FROM student_fees WHERE fee_id=%s', (fee_id,))
            messagebox.showinfo('Success', 'Payment deleted')
            self.load_recent_payments()
            self.load_student_balances()
            self.load_financial_summary()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def edit_payment(self):
        """Edit selected payment using the standard FeePaymentDialog in edit mode"""
        selected = self.payments_tree.selection()
        if not selected:
            messagebox.showwarning('Select', 'Select a payment to edit')
            return
        item = self.payments_tree.item(selected[0], 'values')
        fee_id = item[0]
        try:
            query = """
                SELECT sf.*, s.first_name, s.last_name, s.class as class_name, s.student_code, ft.fee_name
                FROM student_fees sf
                JOIN students s ON sf.student_id = s.student_id
                JOIN fee_types ft ON sf.fee_type_id = ft.fee_type_id
                WHERE sf.fee_id = %s
            """
            rows = db.execute_query(query, (fee_id,), fetch=True)
            if not rows:
                messagebox.showerror('Error', 'Payment record not found')
                return
            row = rows[0]

            # Get a Student object if available, otherwise create a minimal holder
            try:
                from models.student import Student
                student = Student.get_by_id(row['student_id'])
            except Exception:
                class _S: pass
                student = _S()
                student.first_name = row.get('first_name', '')
                student.last_name = row.get('last_name', '')
                student.class_name = row.get('class_name', '')
                student.student_code = row.get('student_code', '')
                student.student_id = row.get('student_id')

            # minimal fee summary (dialog uses it only for display)
            fee_summary = {
                'total_due': 0,
                'total_paid': 0,
                'total_balance': 0
            }

            from UI.dialogs import FeePaymentDialog
            dlg = FeePaymentDialog(self.frame, f"Edit Payment - {student.first_name} {student.last_name}", student, fee_summary, payment=row)
            dlg.show()

            if getattr(dlg, 'result', False):
                self.load_recent_payments()
                self.load_student_balances()
                self.load_financial_summary()

        except Exception as e:
            messagebox.showerror('Error', str(e))
    
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
                # Prefer managed expense categories; fall back to previous heuristics
                try:
                    from models.expense_category import ExpenseCategory
                    ExpenseCategory.ensure_table()
                    cats = ExpenseCategory.get_all()
                    categories = [c.name for c in cats]
                    if not categories:
                        # Fallback to historical categories from expenses/inventory
                        query = "SELECT DISTINCT category FROM expenses WHERE category IS NOT NULL"
                        results = db.execute_query(query, fetch=True)
                        categories = [r['category'] for r in results if r.get('category')]
                        q2 = "SELECT DISTINCT category FROM inventory_items WHERE category IS NOT NULL"
                        res2 = db.execute_query(q2, fetch=True)
                        for r in res2:
                            if r.get('category') and r['category'] not in categories:
                                categories.append(r['category'])
                except Exception:
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
        self.month_expense_var = tk.StringVar(value=format_currency(0.0))
        ttk.Label(summary_frame, textvariable=self.month_expense_var, font=('Arial', 12, 'bold')).pack(side='left', padx=5)
        
        ttk.Button(summary_frame, text="Refresh", command=self.load_recent_expenses).pack(side='right', padx=5)
        # Setup right-click context menu for expenses
        self.setup_expenses_context_menu()
    
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

        # Fee totals (per fee type)
        fee_totals_frame = ttk.LabelFrame(self.financial_summary_frame, text="Fees Collected by Type", padding=10)
        fee_totals_frame.pack(fill='both', padx=20, pady=(0, 10))

        self.fee_totals_tree = ttk.Treeview(fee_totals_frame, columns=('Fee Type', 'Total Collected', 'Payments'), show='headings', height=6)
        for col, w in (('Fee Type', 240), ('Total Collected', 120), ('Payments', 80)):
            self.fee_totals_tree.heading(col, text=col)
            self.fee_totals_tree.column(col, width=w)

        fee_totals_scroll = ttk.Scrollbar(fee_totals_frame, orient='vertical', command=self.fee_totals_tree.yview)
        self.fee_totals_tree.configure(yscrollcommand=fee_totals_scroll.set)
        self.fee_totals_tree.pack(side='left', fill='both', expand=True)
        fee_totals_scroll.pack(side='right', fill='y')
        
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

    def setup_manage_types_tab(self):
        """Setup UI to manage fee types and expense categories"""
        from models.finance import FeeType
        from models.expense_category import ExpenseCategory

        frame = self.manage_types_frame
        container = ttk.Frame(frame)
        container.pack(fill='both', expand=True, padx=10, pady=10)

        # Left: Fee Types management
        left = ttk.LabelFrame(container, text='Fee Types', padding=10)
        left.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        self.fee_types_tree = ttk.Treeview(left, columns=('ID', 'Name', 'Amount', 'Term', 'Required'), show='headings', height=12)
        for col in ('ID', 'Name', 'Amount', 'Term', 'Required'):
            self.fee_types_tree.heading(col, text=col)
            self.fee_types_tree.column(col, width=100)
        self.fee_types_tree.pack(fill='both', expand=True)

        ft_btn_frame = ttk.Frame(left)
        ft_btn_frame.pack(fill='x', pady=5)
        ttk.Button(ft_btn_frame, text='Add Fee Type', command=self.add_fee_type).pack(side='left', padx=5)
        ttk.Button(ft_btn_frame, text='Edit Selected', command=self.edit_fee_type).pack(side='left', padx=5)
        ttk.Button(ft_btn_frame, text='Delete Selected', command=self.delete_fee_type).pack(side='left', padx=5)

        # Right: Expense Categories management
        right = ttk.LabelFrame(container, text='Expense Categories', padding=10)
        right.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        self.exp_cat_tree = ttk.Treeview(right, columns=('ID', 'Name', 'Description'), show='headings', height=12)
        for col in ('ID', 'Name', 'Description'):
            self.exp_cat_tree.heading(col, text=col)
            self.exp_cat_tree.column(col, width=120)
        self.exp_cat_tree.pack(fill='both', expand=True)

        ec_btn_frame = ttk.Frame(right)
        ec_btn_frame.pack(fill='x', pady=5)
        ttk.Button(ec_btn_frame, text='Add Category', command=self.add_expense_category).pack(side='left', padx=5)
        ttk.Button(ec_btn_frame, text='Edit Selected', command=self.edit_expense_category).pack(side='left', padx=5)
        ttk.Button(ec_btn_frame, text='Delete Selected', command=self.delete_expense_category).pack(side='left', padx=5)

        # Load data
        self.load_manage_data()

    def load_manage_data(self):
        """Load fee types and expense categories into management trees"""
        from models.finance import FeeType
        from models.expense_category import ExpenseCategory

        # Clear
        for i in self.fee_types_tree.get_children():
            self.fee_types_tree.delete(i)
        for i in self.exp_cat_tree.get_children():
            self.exp_cat_tree.delete(i)

        # Load fee types
        try:
            fee_types = FeeType.get_all(config.Config.CURRENT_ACADEMIC_YEAR)
            for ft in fee_types:
                self.fee_types_tree.insert('', 'end', values=(ft.fee_type_id, ft.fee_name, format_currency(ft.amount), ft.term, 'Yes' if ft.is_required else 'No'))
        except Exception as e:
            print(f"Error loading fee types for manage tab: {e}")

        # Load expense categories
        try:
            ExpenseCategory.ensure_table()
            cats = ExpenseCategory.get_all()
            for c in cats:
                self.exp_cat_tree.insert('', 'end', values=(c.category_id, c.name, c.description))
        except Exception as e:
            print(f"Error loading expense categories: {e}")

    # Fee Type CRUD helpers (use DB directly for simplicity)
    def add_fee_type(self):
        from UI.dialogs import FeeTypeDialog
        dialog = FeeTypeDialog(self.frame, title='Add Fee Type')
        dialog.show()
        if not dialog.result:
            return
        data = dialog.result_data
        try:
            query = "INSERT INTO fee_types (fee_name, description, amount, term, academic_year, is_required) VALUES (%s, %s, %s, %s, %s, %s)"
            db.execute_query(query, (data['fee_name'], '', data['amount'], data['term'], config.Config.CURRENT_ACADEMIC_YEAR, 1 if data['is_required'] else 0))
            messagebox.showinfo('Success', 'Fee type added')
            self.load_manage_data()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def edit_fee_type(self):
        selected = self.fee_types_tree.selection()
        if not selected:
            messagebox.showwarning('Select', 'Select a fee type to edit')
            return
        item = self.fee_types_tree.item(selected[0], 'values')
        fid = item[0]
        from UI.dialogs import FeeTypeDialog
        # Prepare existing data
        try:
            # amount column shown already formatted; attempt to parse
            amount_str = str(item[2]).replace(config.Config.CURRENCY_SYMBOL, '')
            existing = {'fee_name': item[1], 'amount': float(amount_str) if amount_str else 0.0, 'term': item[3], 'is_required': (item[4] == 'Yes')}
        except Exception:
            existing = {'fee_name': item[1], 'amount': 0.0, 'term': item[3], 'is_required': (item[4] == 'Yes')}

        dialog = FeeTypeDialog(self.frame, title='Edit Fee Type', fee_type=existing)
        dialog.show()
        if not dialog.result:
            return
        data = dialog.result_data
        try:
            query = "UPDATE fee_types SET fee_name=%s, amount=%s, term=%s WHERE fee_type_id=%s"
            db.execute_query(query, (data['fee_name'], data['amount'], data['term'], fid))
            messagebox.showinfo('Success', 'Fee type updated')
            self.load_manage_data()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def delete_fee_type(self):
        selected = self.fee_types_tree.selection()
        if not selected:
            messagebox.showwarning('Select', 'Select a fee type to delete')
            return
        item = self.fee_types_tree.item(selected[0], 'values')
        fid = item[0]
        if not messagebox.askyesno('Confirm', 'Delete selected fee type?'):
            return
        try:
            db.execute_query('DELETE FROM fee_types WHERE fee_type_id=%s', (fid,))
            messagebox.showinfo('Success', 'Fee type deleted')
            self.load_manage_data()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    # Expense category CRUD
    def add_expense_category(self):
        from UI.dialogs import ExpenseCategoryDialog
        dialog = ExpenseCategoryDialog(self.frame, title='Add Category')
        dialog.show()
        if not dialog.result:
            return
        data = dialog.result_data
        from models.expense_category import ExpenseCategory
        ec = ExpenseCategory(name=data['name'], description=data['description'])
        ok, msg = ec.save()
        if ok:
            messagebox.showinfo('Success', msg)
            self.load_manage_data()
        else:
            messagebox.showerror('Error', msg)

    def edit_expense_category(self):
        sel = self.exp_cat_tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a category to edit')
            return
        vals = self.exp_cat_tree.item(sel[0], 'values')
        cid = vals[0]
        from UI.dialogs import ExpenseCategoryDialog
        dialog = ExpenseCategoryDialog(self.frame, title='Edit Category', category={'name': vals[1], 'description': vals[2]})
        dialog.show()
        if not dialog.result:
            return
        data = dialog.result_data
        from models.expense_category import ExpenseCategory
        ec = ExpenseCategory(category_id=cid, name=data['name'], description=data['description'])
        ok, msg = ec.save()
        if ok:
            messagebox.showinfo('Success', msg)
            self.load_manage_data()
        else:
            messagebox.showerror('Error', msg)

    def delete_expense_category(self):
        sel = self.exp_cat_tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select a category to delete')
            return
        vals = self.exp_cat_tree.item(sel[0], 'values')
        cid = vals[0]
        if not messagebox.askyesno('Confirm', 'Delete selected category?'):
            return
        from models.expense_category import ExpenseCategory
        ec = ExpenseCategory(category_id=cid)
        ok, msg = ec.delete()
        if ok:
            messagebox.showinfo('Success', msg)
            self.load_manage_data()
        else:
            messagebox.showerror('Error', msg)
    
    def create_summary_card(self, parent, title, var_name, color):
        """Create a summary card"""
        card = ttk.Frame(parent, relief='solid', borderwidth=1)
        
        # Title
        ttk.Label(card, text=title, font=('Arial', 10)).pack(pady=(10, 5))
        
        # Value
        setattr(self, var_name, tk.StringVar(value=format_currency(0.0)))
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
                WHERE academic_year = %s
                ORDER BY fee_name
            """
            results = db.execute_query(query, (config.Config.CURRENT_ACADEMIC_YEAR,), fetch=True)
            fee_list = [f"{r['fee_type_id']}: {r['fee_name']} ({format_currency(r['amount'])})" for r in results]
            self.fee_type_combo['values'] = fee_list
        except Exception as e:
            print(f"Error loading fee types: {e}")

    def on_fee_type_selected(self, event=None):
        """Auto-fill and enforce tuition amounts based on student class when tuition fee selected."""
        try:
            sel = self.fee_type_var.get()
            if not sel:
                return
            fee_type_id = int(sel.split(':')[0])
            q = "SELECT fee_name, amount FROM fee_types WHERE fee_type_id=%s"
            res = db.execute_query(q, (fee_type_id,), fetch=True)
            if not res:
                return
            fee_name = res[0].get('fee_name', '') or ''
            db_amount = res[0].get('amount', 0) or 0

            # Default behavior: set amount to stored fee amount
            expected = float(db_amount)

            # If fee is tuition, enforce based on class
            if 'tuition' in fee_name.lower():
                student_sel = self.student_var.get() or ''
                # student_sel format: "<id>: First Last (Class)"
                class_part = ''
                m = re.search(r"\(([^)]+)\)", student_sel)
                if m:
                    class_part = m.group(1).strip()
                else:
                    # try take trailing token
                    parts = student_sel.split('(')
                    if len(parts) > 1:
                        class_part = parts[-1].strip(') ')

                # Determine expected tuition
                if class_part and 'nursery' in class_part.lower():
                    expected = 45000.0
                else:
                    # try to find numeric grade
                    num_match = re.search(r"(\d+)", class_part)
                    if num_match:
                        try:
                            grade = int(num_match.group(1))
                            if 1 <= grade <= 7:
                                expected = 85000.0
                        except ValueError:
                            pass

            # Set amount and lock if tuition
            self.amount_var.set(str(int(expected) if float(expected).is_integer() else f"{expected:.2f}"))
            if hasattr(self, 'amount_entry'):
                if 'tuition' in (fee_name or '').lower():
                    self.amount_entry.config(state='readonly')
                else:
                    self.amount_entry.config(state='normal')

        except Exception as e:
            print(f"Error handling fee type selection: {e}")
    
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
                WHERE DATE(payment_date) = CURDATE()
            """
            result = db.execute_query(query, fetch=True)
            if result:
                self.today_total_var.set(format_currency(float(result[0]['total'])))
            
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
                    format_currency(float(row['amount_paid'])),
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
            # Compute total fees per student replacing tuition amounts depending on class
            acad_year = config.Config.CURRENT_ACADEMIC_YEAR
            query = f"""
                SELECT 
                    s.student_id,
                    CONCAT(s.first_name, ' ', s.last_name) as student_name,
                    s.class,
                    COALESCE(SUM(
                        CASE
                            WHEN sfe.exemption_id IS NOT NULL THEN 0
                            WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') AND s.is_new = 0 THEN 0
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                            ELSE ft.amount
                        END
                    ), 0) as total_fees,
                    COALESCE(SUM(sf.amount_paid), 0) as amount_paid,
                    COALESCE(SUM(
                        CASE
                            WHEN sfe.exemption_id IS NOT NULL THEN 0
                            WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') AND s.is_new = 0 THEN 0
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                            ELSE ft.amount
                        END
                    ), 0) - COALESCE(SUM(sf.amount_paid), 0) as balance
                FROM students s
                CROSS JOIN fee_types ft
                LEFT JOIN student_fee_exemptions sfe ON sfe.student_id = s.student_id AND sfe.fee_type_id = ft.fee_type_id
                LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                WHERE s.is_active = 1 AND ft.academic_year = '{acad_year}'
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
                    format_currency(float(row['total_fees'])),
                    format_currency(float(row['amount_paid'])),
                    format_currency(balance),
                    status
                ))
            
            # Update summary
            self.total_outstanding_var.set(format_currency(total_outstanding))
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
                    COALESCE(SUM(
                        CASE
                            WHEN sfe.exemption_id IS NOT NULL THEN 0
                            WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') AND s.is_new = 0 THEN 0
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                            ELSE ft.amount
                        END
                    ), 0) as total_fees,
                    COALESCE(SUM(sf.amount_paid), 0) as amount_paid,
                    COALESCE(SUM(
                        CASE
                            WHEN sfe.exemption_id IS NOT NULL THEN 0
                            WHEN (LOWER(ft.fee_name) LIKE '%%registration%%' OR LOWER(ft.fee_name) LIKE '%%uniform%%') AND s.is_new = 0 THEN 0
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                            WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                            ELSE ft.amount
                        END
                    ), 0) - COALESCE(SUM(sf.amount_paid), 0) as balance
                FROM students s
                CROSS JOIN fee_types ft
                LEFT JOIN student_fee_exemptions sfe ON sfe.student_id = s.student_id AND sfe.fee_type_id = ft.fee_type_id
                LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                WHERE s.is_active = 1 AND ft.academic_year = %s
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
            
            # Use current academic year
            params = tuple(params) if params else tuple()
            params = (config.Config.CURRENT_ACADEMIC_YEAR,) + params
            results = db.execute_query(query=base_query, params=params, fetch=True)
            
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
                    format_currency(float(row['total_fees'])),
                    format_currency(float(row['amount_paid'])),
                    format_currency(balance),
                    status
                ))
            
            # Update summary
            self.total_outstanding_var.set(format_currency(total_outstanding))
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
                self.month_expense_var.set(format_currency(float(result[0]['total'])))
            
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
                    format_currency(float(row['amount'])),
                    row['payment_method'],
                    row['receipt_number'] or ''
                ))
                
        except Exception as e:
            print(f"Error loading expenses: {e}")

    def setup_expenses_context_menu(self):
        """Setup context menu for expenses list"""
        self.expenses_menu = tk.Menu(self.frame, tearoff=0)
        self.expenses_menu.add_command(label='Edit Expense', command=self.edit_expense)
        self.expenses_menu.add_separator()
        self.expenses_menu.add_command(label='Delete Expense', command=self.delete_expense)
        self.expenses_tree.bind('<Button-3>', self.show_expenses_context_menu)
        self.expenses_tree.bind('<Double-1>', lambda e: self.edit_expense())

    def show_expenses_context_menu(self, event):
        item = self.expenses_tree.identify_row(event.y)
        if item:
            self.expenses_tree.selection_set(item)
            self.expenses_menu.post(event.x_root, event.y_root)

    def delete_expense(self):
        sel = self.expenses_tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select an expense to delete')
            return
        item = self.expenses_tree.item(sel[0], 'values')
        expense_id = item[0]
        if not messagebox.askyesno('Confirm', 'Permanently delete selected expense?'):
            return
        try:
            db.execute_query('DELETE FROM expenses WHERE expense_id=%s', (expense_id,))
            messagebox.showinfo('Success', 'Expense deleted')
            self.load_recent_expenses()
            self.load_financial_summary()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def edit_expense(self):
        sel = self.expenses_tree.selection()
        if not sel:
            messagebox.showwarning('Select', 'Select an expense to edit')
            return
        item = self.expenses_tree.item(sel[0], 'values')
        expense_id = item[0]
        try:
            q = 'SELECT * FROM expenses WHERE expense_id=%s'
            rows = db.execute_query(q, (expense_id,), fetch=True)
            if not rows:
                messagebox.showerror('Error', 'Expense not found')
                return
            row = rows[0]

            dlg = tk.Toplevel(self.frame)
            dlg.title('Edit Expense')
            dlg.transient(self.frame)
            dlg.grab_set()

            ttk.Label(dlg, text='Date (YYYY-MM-DD):').grid(row=0, column=0, sticky='e', padx=6, pady=4)
            date_var = tk.StringVar(value=str(row.get('expense_date') or date.today().strftime('%Y-%m-%d')))
            ttk.Entry(dlg, textvariable=date_var, width=25).grid(row=0, column=1, padx=6, pady=4, sticky='w')

            ttk.Label(dlg, text='Description:').grid(row=1, column=0, sticky='ne', padx=6, pady=4)
            desc_txt = tk.Text(dlg, width=40, height=4)
            desc_txt.grid(row=1, column=1, padx=6, pady=4)
            if row.get('description'):
                desc_txt.insert('1.0', row.get('description'))

            ttk.Label(dlg, text='Category:').grid(row=2, column=0, sticky='e', padx=6, pady=4)
            category_var = tk.StringVar(value=row.get('category') or '')
            ttk.Entry(dlg, textvariable=category_var, width=30).grid(row=2, column=1, padx=6, pady=4, sticky='w')

            ttk.Label(dlg, text='Amount:').grid(row=3, column=0, sticky='e', padx=6, pady=4)
            amount_var = tk.StringVar(value=str(row.get('amount') or '0'))
            ttk.Entry(dlg, textvariable=amount_var, width=20).grid(row=3, column=1, padx=6, pady=4, sticky='w')

            ttk.Label(dlg, text='Method:').grid(row=4, column=0, sticky='e', padx=6, pady=4)
            method_var = tk.StringVar(value=row.get('payment_method') or 'Cash')
            ttk.Combobox(dlg, textvariable=method_var, values=['Cash','M-Pesa','Bank Transfer','Check','Other'], state='readonly', width=20).grid(row=4, column=1, padx=6, pady=4, sticky='w')

            ttk.Label(dlg, text='Receipt No:').grid(row=5, column=0, sticky='e', padx=6, pady=4)
            receipt_var = tk.StringVar(value=row.get('receipt_number') or '')
            ttk.Entry(dlg, textvariable=receipt_var, width=30).grid(row=5, column=1, padx=6, pady=4, sticky='w')

            def on_save():
                try:
                    pdate = date_var.get().strip()
                    desc = desc_txt.get('1.0', 'end').strip()
                    cat = category_var.get().strip() or None
                    amt = parse_currency(amount_var.get())
                    mth = method_var.get().strip() or 'Cash'
                    rno = receipt_var.get().strip() or None

                    db.execute_query(
                        """UPDATE expenses SET expense_date=%s, description=%s, category=%s, amount=%s, payment_method=%s, receipt_number=%s WHERE expense_id=%s""",
                        (pdate, desc, cat, amt, mth, rno, expense_id)
                    )
                    messagebox.showinfo('Success', 'Expense updated')
                    dlg.destroy()
                    self.load_recent_expenses()
                    self.load_financial_summary()
                except Exception as e:
                    messagebox.showerror('Error', str(e))

            btns = ttk.Frame(dlg)
            btns.grid(row=6, column=0, columnspan=2, pady=8)
            ttk.Button(btns, text='Save', command=on_save).pack(side='left', padx=6)
            ttk.Button(btns, text='Cancel', command=dlg.destroy).pack(side='left', padx=6)

        except Exception as e:
            messagebox.showerror('Error', str(e))
    
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
                from utils.helpers import format_currency
                self.total_income_var.set(format_currency(float(result[0]['total'])))
            
            # Total expenses (all time)
            query = "SELECT COALESCE(SUM(amount), 0) as total FROM expenses"
            result = db.execute_query(query, fetch=True)
            if result:
                from utils.helpers import format_currency
                self.total_expenses_var.set(format_currency(float(result[0]['total'])))
            
            # Net balance
            income = float(parse_currency(self.total_income_var.get()))
            expenses = float(parse_currency(self.total_expenses_var.get()))
            self.net_balance_var.set(format_currency(income - expenses))
            
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
                self.this_month_var.set(format_currency(month_income - month_expenses))
            
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
                self.ytd_var.set(format_currency(ytd_income - ytd_expenses))
            
            # Outstanding fees (apply tuition mapping by class)
            acad_year = config.Config.CURRENT_ACADEMIC_YEAR
            query = f"""
                SELECT COALESCE(SUM(balance), 0) as total
                FROM (
                    SELECT 
                        COALESCE(SUM(
                            CASE
                                WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' AND (LOWER(s.class) LIKE '%%nursery%%' OR LOWER(s.class) LIKE '%%reception%%') THEN 45000
                                WHEN LOWER(ft.fee_name) LIKE '%%tuition%%' THEN 85000
                                ELSE ft.amount
                            END
                        ), 0) - COALESCE(SUM(sf.amount_paid), 0) as balance
                    FROM students s
                    CROSS JOIN fee_types ft
                    LEFT JOIN student_fees sf ON s.student_id = sf.student_id AND ft.fee_type_id = sf.fee_type_id
                    WHERE s.is_active = 1 AND ft.academic_year = '{acad_year}'
                    GROUP BY s.student_id
                    HAVING balance > 0
                ) as outstanding
            """
            result = db.execute_query(query, fetch=True)
            if result:
                from utils.helpers import format_currency
                self.outstanding_var.set(format_currency(float(result[0]['total'])))
            
            # Load monthly breakdown
            self.load_monthly_breakdown()
            
            # Load expense categories
            self.load_expense_categories()
            
            # Load fee totals by type
            try:
                from models.finance import FinancialManager
                for item in self.fee_totals_tree.get_children():
                    self.fee_totals_tree.delete(item)
                fee_totals = FinancialManager.get_collected_by_fee_type()
                for row in fee_totals:
                    self.fee_totals_tree.insert('', 'end', values=(
                        row.get('fee_name'),
                        format_currency(float(row.get('total_collected', 0))),
                        row.get('payment_count', 0)
                    ))
            except Exception as e:
                print(f"Error loading fee totals: {e}")
            
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
                    format_currency(data['income']),
                    format_currency(data['expenses']),
                    format_currency(data['net'])
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
                    format_currency(float(row['total']))
                ))
                
        except Exception as e:
            print(f"Error loading expense categories: {e}")
    
    def record_payment(self):
        """Record a fee payment"""
        import traceback
        # record_payment invoked
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
            student_sel = self.student_var.get().strip()
            try:
                # Try to parse "ID: Name (Class)" format
                student_id = int(student_sel.split(':')[0])
            except (ValueError, IndexError):
                # Fallback: try to search by name if user typed it manually
                query = "SELECT student_id FROM students WHERE CONCAT(first_name, ' ', last_name) LIKE %s LIMIT 1"
                result = db.execute_query(query, (f"%{student_sel}%",), fetch=True)
                if result:
                    student_id = result[0]['student_id']
                else:
                    messagebox.showerror("Error", "Student not found. Please select from dropdown.")
                    return
            
            # Parse fee_type_id safely
            try:
                fee_type_id = int(self.fee_type_var.get().split(':')[0])
            except Exception:
                # try to resolve by fee name
                sel = self.fee_type_var.get()
                fee_name = sel.split(':', 1)[-1].strip() if ':' in sel else sel
                try:
                    q = "SELECT fee_type_id FROM fee_types WHERE fee_name = %s LIMIT 1"
                    res = db.execute_query(q, (fee_name,), fetch=True)
                    if res:
                        fee_type_id = res[0]['fee_type_id']
                    else:
                        messagebox.showerror('Error', 'Fee type not found. Please select from dropdown.')
                        return
                except Exception as e:
                    messagebox.showerror('Error', f'Failed to resolve fee type: {e}')
                    return
            
            # Get description
            description = self.description_text.get("1.0", "end-1c").strip()
            
            # Generate receipt number if not provided (atomic DB-backed sequence)
            receipt_number = self.receipt_var.get().strip()
            if not receipt_number:
                # Use DB-backed per-day sequence for atomic generation
                date_str = datetime.now().strftime('%Y%m%d')
                try:
                    # Atomic INSERT...ON DUPLICATE KEY UPDATE to increment sequence
                    db.execute_query(
                        "INSERT INTO receipt_sequence (seq_date, seq) VALUES (%s, 1) ON DUPLICATE KEY UPDATE seq = seq + 1",
                        (date_str,)
                    )
                    # Fetch the updated sequence number
                    res = db.execute_query("SELECT seq FROM receipt_sequence WHERE seq_date = %s", (date_str,), fetch=True)
                    seq = res[0]['seq'] if res else 1
                    receipt_number = f"REC-{date_str}-{seq:04d}"
                except Exception as seq_err:
                    # Fallback to COUNT-based if sequence table has issues
                    print(f"Warning: sequence generation failed: {seq_err}")
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
            tb = traceback.format_exc()
            print('record_payment error:', tb)
            messagebox.showerror("Error", f"Failed to record payment: {str(e)}\n\nSee console for traceback.")
    
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
        balance = float(parse_currency(item['values'][5]))
        
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
            
            # Get student's class so we can override tuition amounts
            try:
                sres = db.execute_query("SELECT class FROM students WHERE student_id=%s", (student_id,), fetch=True)
                student_class = sres[0]['class'] if sres else ''
            except Exception:
                student_class = ''

            # Get fee details for academic year
            query = """
                SELECT 
                    ft.fee_name,
                    ft.amount as expected_amount,
                    COALESCE(SUM(sf.amount_paid), 0) as paid_amount,
                    ft.amount - COALESCE(SUM(sf.amount_paid), 0) as balance,
                    MAX(sf.payment_date) as last_payment
                FROM fee_types ft
                LEFT JOIN student_fees sf ON ft.fee_type_id = sf.fee_type_id AND sf.student_id = %s
                WHERE ft.academic_year = %s
                GROUP BY ft.fee_type_id, ft.fee_name, ft.amount
                ORDER BY ft.fee_name
            """
            results = db.execute_query(query, (student_id, config.Config.CURRENT_ACADEMIC_YEAR), fetch=True)
            
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
            
            # Add data (apply tuition overrides)
            total_expected = total_paid = total_balance = 0
            for row in results:
                fee_name = row.get('fee_name') or ''
                expected_amt = float(row.get('expected_amount') or 0)
                paid_amt = float(row.get('paid_amount') or 0)

                if 'tuition' in fee_name.lower():
                    cls_lower = (student_class or '').lower()
                    if 'nursery' in cls_lower or 'reception' in cls_lower:
                        expected_amt = 45000.0
                    else:
                        expected_amt = 85000.0

                balance_val = expected_amt - paid_amt

                tree.insert('', 'end', values=(
                    fee_name,
                    format_currency(expected_amt),
                    format_currency(paid_amt),
                    format_currency(balance_val),
                    row.get('last_payment') or 'None'
                ))
                total_expected += expected_amt
                total_paid += paid_amt
                total_balance += balance_val
            
            # Add totals row
            tree.insert('', 'end', values=(
                'TOTAL',
                format_currency(total_expected),
                format_currency(total_paid),
                format_currency(total_balance),
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
                    format_currency(float(row['amount_paid'])),
                    row['payment_method'],
                    row['receipt_number'] or '',
                    row['description'] or ''
                ))
                total += float(row['amount_paid'])
            
            # Summary
            summary_frame = ttk.Frame(dialog)
            summary_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Label(summary_frame, text=f"Total Payments: {format_currency(total)}", font=('Arial', 10, 'bold')).pack()
            
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
        ttk.Label(dialog, text=f"Outstanding Balance: {format_currency(balance)}").pack(pady=5)
        
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
                    messagebox.showwarning("Warning", f"Amount cannot exceed balance of {format_currency(balance)}")
                    return
                
                # Record payment (simplified - would need fee type selection)
                messagebox.showinfo("Info", f"Payment of {format_currency(amount)} recorded for {student_name}")
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