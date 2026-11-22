import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import re
import json
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
        self._finance_view_loading = False
        self.finance_view_year_var = tk.StringVar(value=config.Config.CURRENT_ACADEMIC_YEAR)
        self.finance_view_term_var = tk.StringVar(value=config.Config.CURRENT_TERM)
        self.finance_view_term_var.trace_add('write', lambda *_: self.on_finance_view_changed())

        # Create notebook for different finance sections
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.fee_payments_frame = ttk.Frame(self.notebook)
        self.student_balances_frame = ttk.Frame(self.notebook)
        self.expenses_frame = ttk.Frame(self.notebook)
        self.financial_summary_frame = ttk.Frame(self.notebook)
        self.staff_salaries_frame = ttk.Frame(self.notebook)
        self.term_rollover_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.fee_payments_frame, text="Fee Payments")
        self.notebook.add(self.student_balances_frame, text="Student Balances")
        self.notebook.add(self.term_rollover_frame, text="Term Rollover")
        self.notebook.add(self.expenses_frame, text="Expenses")
        self.notebook.add(self.financial_summary_frame, text="Financial Summary")
        self.notebook.add(self.staff_salaries_frame, text="Staff Salaries")
        # Management tab for fee types and expense categories
        self.manage_types_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.manage_types_frame, text="Manage Types")
        
        # Setup each tab
        self.setup_fee_payments_tab()
        self.setup_student_balances_tab()
        self.setup_term_rollover_tab()
        self.setup_expenses_tab()
        self.setup_financial_summary_tab()
        self.setup_staff_salaries_tab()
        self.setup_manage_types_tab()

    def _current_finance_view(self):
        """Return the selected academic year and term for finance views."""
        year = (self.finance_view_year_var.get() or config.Config.CURRENT_ACADEMIC_YEAR).strip()
        term = (self.finance_view_term_var.get() or config.Config.CURRENT_TERM).strip()
        return year, term

    def _sync_finance_view_headers(self):
        """Refresh term header labels in finance pages."""
        year, term = self._current_finance_view()
        start_date, end_date = config.Config.get_term_date_range(term)
        if start_date and end_date:
            label = f"Viewing {year} | {term} | {start_date} to {end_date}"
        else:
            label = f"Viewing {year} | {term}"
        if hasattr(self, 'expenses_term_info_var'):
            self.expenses_term_info_var.set(label)
        if hasattr(self, 'summary_term_info_var'):
            self.summary_term_info_var.set(label)

    def _step_finance_term(self, offset: int):
        """Move finance views backward or forward across configured terms."""
        terms = list(getattr(config.Config, 'TERMS', ['Term 1', 'Term 2', 'Term 3'])) or ['Term 1', 'Term 2', 'Term 3']
        current = self.finance_view_term_var.get() or config.Config.CURRENT_TERM
        if current not in terms:
            current = terms[0]
        index = terms.index(current)
        self.finance_view_term_var.set(terms[(index + offset) % len(terms)])

    def reset_finance_view(self):
        """Reset finance pages to the active configured term."""
        self._finance_view_loading = True
        try:
            self.finance_view_year_var.set(config.Config.CURRENT_ACADEMIC_YEAR)
            self.finance_view_term_var.set(config.Config.CURRENT_TERM)
        finally:
            self._finance_view_loading = False
        self._sync_finance_view_headers()

    def on_finance_view_changed(self, event=None):
        """Refresh term-aware finance pages when the selected term changes."""
        if getattr(self, '_finance_view_loading', False):
            return
        self._sync_finance_view_headers()
        if hasattr(self, 'expenses_tree'):
            self.load_recent_expenses()
        if hasattr(self, 'total_income_var'):
            self.load_financial_summary()
    
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
        self.student_combo.bind('<<ComboboxSelected>>', self.on_student_selected)
        
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
        methods = ['Cash', 'Mobile money', 'Bank Transfer', 'Check', 'Other']
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
        
        # Payments table
        table_frame = ttk.LabelFrame(right_frame, text="Payments", padding=10)
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

        # Filter frame for payments (filter by student or fee type)
        filter_frame = ttk.Frame(right_frame)
        filter_frame.pack(fill='x', pady=(5, 10))

        # Laid out as a small grid: one long row squeezed the controls on small screens.
        ttk.Label(filter_frame, text='Filter by Fee Type:').grid(row=0, column=0, sticky='w', padx=(0, 5), pady=2)
        self.filter_fee_var = tk.StringVar()
        self.filter_fee_combo = ttk.Combobox(filter_frame, textvariable=self.filter_fee_var, width=30)
        self.filter_fee_combo.grid(row=0, column=1, sticky='w', pady=2)

        ttk.Label(filter_frame, text='Filter by Student:').grid(row=1, column=0, sticky='w', padx=(0, 5), pady=2)
        self.filter_student_var = tk.StringVar()
        self.filter_student_combo = ttk.Combobox(filter_frame, textvariable=self.filter_student_var, width=30)
        self.filter_student_combo.grid(row=1, column=1, sticky='w', pady=2)

        actions = ttk.Frame(filter_frame)
        actions.grid(row=2, column=0, columnspan=2, sticky='w', pady=(4, 0))
        self.show_all_payments_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            actions,
            text='Show all payments',
            variable=self.show_all_payments_var,
            command=self.load_recent_payments
        ).pack(side='left', padx=(0, 10))
        ttk.Button(actions, text='Search', command=self.search_payments).pack(side='left', padx=(0, 4))
        ttk.Button(actions, text='Clear', command=lambda: (self.filter_fee_var.set(''), self.filter_student_var.set(''), self.load_recent_payments())).pack(side='left')
    
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
        status_options = ['All', 'Paid', 'Partial', 'Unpaid', 'Carried Forward']
        ttk.Combobox(top_frame, textvariable=self.balance_status_var, values=status_options, width=10).pack(side='left', padx=5)

        # Fee Type filter (new)
        ttk.Label(top_frame, text="Fee Type:").pack(side='left', padx=5)
        self.balance_fee_var = tk.StringVar(value="")
        self.balance_fee_combo = ttk.Combobox(top_frame, textvariable=self.balance_fee_var, width=30)
        self.balance_fee_combo.pack(side='left', padx=5)
        self.balance_fee_combo.bind('<<ComboboxSelected>>', lambda e: self.load_student_balances())
        
        # Search
        ttk.Label(top_frame, text="Search:").pack(side='left', padx=5)
        self.balance_search_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.balance_search_var, width=20).pack(side='left', padx=5)
        
        ttk.Button(top_frame, text="Search", command=self.search_balances).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Clear", command=lambda: (self.balance_class_var.set('All'), self.balance_status_var.set('All'), self.balance_fee_var.set(''), self.balance_search_var.set(''), self.load_student_balances())).pack(side='left', padx=5)
        
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

    def setup_term_rollover_tab(self):
        """Setup dedicated term rollover management UI."""
        header = ttk.LabelFrame(self.term_rollover_frame, text="Term Rollover Management", padding=12)
        header.pack(fill='x', padx=10, pady=10)

        ttk.Label(header, text="Current Term:").grid(row=0, column=0, sticky='w', padx=4, pady=4)
        self.rollover_current_term_var = tk.StringVar()
        ttk.Label(header, textvariable=self.rollover_current_term_var, font=('Arial', 11, 'bold')).grid(row=0, column=1, sticky='w', padx=4, pady=4)

        # The next period is derived, never chosen: after the last term the
        # academic year moves forward (see FinancialManager._resolve_rollover_target).
        ttk.Label(header, text="Next Term:").grid(row=0, column=2, sticky='w', padx=(20, 4), pady=4)
        self.rollover_next_term_var = tk.StringVar()
        self.rollover_next_year_var = tk.StringVar()
        self.rollover_next_period_var = tk.StringVar()
        ttk.Label(header, textvariable=self.rollover_next_period_var, font=('Arial', 11, 'bold')).grid(row=0, column=3, sticky='w', padx=4, pady=4)

        ttk.Label(header, text="New Term Start Date:").grid(row=0, column=4, sticky='w', padx=(20, 4), pady=4)
        # Left blank on purpose: the new term's start must come after the closing term ends.
        self.rollover_start_date_var = tk.StringVar(value='')
        ttk.Entry(header, textvariable=self.rollover_start_date_var, width=16).grid(row=0, column=5, sticky='w', padx=4, pady=4)

        ttk.Label(header, text="Class Filter:").grid(row=1, column=0, sticky='w', padx=4, pady=4)
        self.rollover_class_var = tk.StringVar(value='All')
        self.rollover_class_combo = ttk.Combobox(header, textvariable=self.rollover_class_var, width=16, state='readonly')
        self.rollover_class_combo.grid(row=1, column=1, sticky='w', padx=4, pady=4)
        self.rollover_class_combo.bind('<<ComboboxSelected>>', lambda e: self._render_rollover_preview())

        ttk.Label(header, text="Student Search:").grid(row=1, column=2, sticky='w', padx=(20, 4), pady=4)
        self.rollover_search_var = tk.StringVar()
        search_entry = ttk.Entry(header, textvariable=self.rollover_search_var, width=24)
        search_entry.grid(row=1, column=3, sticky='w', padx=4, pady=4)
        search_entry.bind('<KeyRelease>', lambda e: self._render_rollover_preview())

        ttk.Label(header, text="Status:").grid(row=1, column=4, sticky='w', padx=(20, 4), pady=4)
        self.rollover_status_var = tk.StringVar(value='All')
        status_combo = ttk.Combobox(
            header,
            textvariable=self.rollover_status_var,
            values=['All', 'Paid', 'Partial', 'Unpaid', 'Carried Forward', 'Credit', 'Reset'],
            width=16,
            state='readonly'
        )
        status_combo.grid(row=1, column=5, sticky='w', padx=4, pady=4)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self._render_rollover_preview())

        button_row = ttk.Frame(header)
        button_row.grid(row=2, column=0, columnspan=6, sticky='w', pady=(8, 0))
        ttk.Button(button_row, text="Preview Rollover", command=self.preview_term_rollover).pack(side='left', padx=4)
        ttk.Button(button_row, text="Execute Rollover", command=self.execute_term_rollover).pack(side='left', padx=4)
        ttk.Button(button_row, text="Refresh", command=self.load_term_rollover_data).pack(side='left', padx=4)
        ttk.Button(button_row, text="Toggle Carry for Selected", command=self.toggle_selected_rollover_carry).pack(side='left', padx=4)
        ttk.Button(button_row, text="Include All Carry", command=self.include_all_rollover_carry).pack(side='left', padx=4)
        ttk.Button(button_row, text="View Selected Details", command=self.show_rollover_item_details).pack(side='left', padx=4)

        summary = ttk.Frame(self.term_rollover_frame)
        summary.pack(fill='x', padx=10, pady=(0, 10))
        cards = [
            ('Students', 'rollover_total_students_var'),
            ('Reset', 'rollover_reset_students_var'),
            ('Carry Forward', 'rollover_carry_students_var'),
            ('Credit Forward', 'rollover_credit_total_var'),
            ('Prev Outstanding', 'rollover_prev_total_var'),
            ('New Term Fees', 'rollover_new_total_var'),
            ('Opening Balance', 'rollover_opening_total_var')
        ]
        for label, var_name in cards:
            card = ttk.LabelFrame(summary, text=label, padding=8)
            card.pack(side='left', fill='x', expand=True, padx=4)
            setattr(self, var_name, tk.StringVar(value='0'))
            ttk.Label(card, textvariable=getattr(self, var_name), font=('Arial', 11, 'bold')).pack(anchor='center')

        ttk.Label(self.term_rollover_frame, text="Preview and Results", font=('Arial', 11, 'bold')).pack(anchor='w', padx=12)
        table_frame = ttk.Frame(self.term_rollover_frame)
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)

        rollover_cols = [
            'ID', 'Include Carry', 'Student', 'Class', 'Prev Outstanding', 'New Term Fees',
            'Carry Forward', 'Reset', 'Opening Balance', 'Status'
        ]
        self.rollover_tree = ttk.Treeview(table_frame, columns=rollover_cols, show='headings', height=18)
        for col in rollover_cols:
            self.rollover_tree.heading(col, text=col)
            self.rollover_tree.column(col, width=120)
        self.rollover_tree.column('ID', width=70)
        self.rollover_tree.column('Include Carry', width=95, anchor='center')
        self.rollover_tree.column('Student', width=180)
        self.rollover_tree.column('Class', width=100)
        self.rollover_tree.column('Status', width=120)

        rollover_scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.rollover_tree.yview)
        self.rollover_tree.configure(yscrollcommand=rollover_scroll.set)
        self.rollover_tree.pack(side='left', fill='both', expand=True)
        rollover_scroll.pack(side='right', fill='y')
        self.rollover_tree.bind('<Button-1>', self._on_rollover_tree_click)
        self.rollover_tree.bind('<space>', lambda e: self.toggle_selected_rollover_carry())
        self.rollover_tree.bind('<Double-1>', lambda e: self.show_rollover_item_details())

        footer = ttk.Frame(self.term_rollover_frame)
        footer.pack(fill='x', padx=10, pady=(0, 10))
        self.rollover_info_var = tk.StringVar(value='Preview the next term before executing rollover.')
        ttk.Label(footer, textvariable=self.rollover_info_var).pack(side='left')
        self._rollover_excluded_carry_ids = set()

    def _update_rollover_summary(self, preview_data=None):
        """Update rollover summary cards from preview data."""
        summary = (preview_data or {}).get('summary') or {}
        self.rollover_total_students_var.set(str(summary.get('total_students', 0)))
        self.rollover_reset_students_var.set(str(summary.get('reset_students', 0)))
        self.rollover_carry_students_var.set(str(summary.get('carry_students', 0)))
        self.rollover_credit_total_var.set(
            f"{summary.get('credit_students', 0)} / {format_currency(float(summary.get('credit_carried_total', 0) or 0))}"
        )
        self.rollover_prev_total_var.set(format_currency(float(summary.get('previous_outstanding_total', 0) or 0)))
        self.rollover_new_total_var.set(format_currency(float(summary.get('new_term_total', 0) or 0)))
        self.rollover_opening_total_var.set(format_currency(float(summary.get('opening_balance_total', 0) or 0)))

    def _filtered_rollover_rows(self, rows):
        """Apply UI filters to rollover preview rows."""
        class_filter = self.rollover_class_var.get() or 'All'
        status_filter = self.rollover_status_var.get() or 'All'
        search_term = (self.rollover_search_var.get() or '').strip().lower()
        out = []
        for row in rows or []:
            if class_filter != 'All' and row.get('class') != class_filter:
                continue
            if status_filter != 'All':
                carry_status = row.get('carry_status') or ''
                pay_status = row.get('payment_status') or ''
                if status_filter in ('Carried Forward', 'Credit', 'Reset'):
                    if carry_status != status_filter:
                        continue
                elif pay_status != status_filter:
                    continue
            if search_term:
                haystack = f"{row.get('student_name', '')} {row.get('student_code', '')}".lower()
                if search_term not in haystack:
                    continue
            out.append(row)
        return out

    def _render_rollover_preview(self):
        """Render rollover rows currently loaded in memory."""
        for item in self.rollover_tree.get_children():
            self.rollover_tree.delete(item)

        rows = self._filtered_rollover_rows(getattr(self, '_rollover_preview_rows', []))
        for row in rows:
            status = row.get('carry_status') if row.get('carry_status') in ('Carried Forward', 'Credit') else row.get('payment_status')
            self.rollover_tree.insert('', 'end', values=(
                row.get('student_id'),
                '[x]' if row.get('include_carry_forward', True) else '[ ]',
                row.get('student_name'),
                row.get('class'),
                format_currency(float(row.get('previous_outstanding') or 0)),
                format_currency(float(row.get('new_term_total') or 0)),
                format_currency(float(row.get('carry_forward_total') or 0)),
                format_currency(float(row.get('reset_amount') or 0)),
                format_currency(float(row.get('opening_balance') or 0)),
                status
            ))

    def load_term_rollover_data(self):
        """Load rollover defaults and latest executed summary."""
        try:
            from models.finance import FinancialManager
            self._refresh_rollover_period_labels()
            self.rollover_class_combo['values'] = tuple(self.balance_class_combo['values']) if self.balance_class_combo['values'] else ('All',)
            latest = FinancialManager.get_latest_rollover_run()
            if latest:
                to_year = latest.get('to_academic_year') or latest.get('academic_year')
                self.rollover_info_var.set(
                    f"Last completed rollover: {latest.get('from_term')} {latest.get('academic_year')} -> "
                    f"{latest.get('to_term')} {to_year} on {latest.get('completed_at') or latest.get('created_at')}"
                )
                self._update_rollover_summary({'summary': {
                    'total_students': latest.get('total_students', 0),
                    'reset_students': latest.get('reset_students', 0),
                    'carry_students': latest.get('carry_students', 0),
                    'previous_outstanding_total': latest.get('previous_outstanding_total', 0),
                    'new_term_total': latest.get('new_term_total', 0),
                    'opening_balance_total': latest.get('opening_balance_total', 0)
                }})
            else:
                self._update_rollover_summary({})
                self.rollover_info_var.set('Preview the next term before executing rollover.')
            self._rollover_preview_rows = []
            self._rollover_preview = None
            self._rollover_excluded_carry_ids = set()
            self._render_rollover_preview()
        except Exception as e:
            print(f"Error loading rollover data: {e}")

    def _refresh_rollover_period_labels(self):
        """Show the closing period and the derived next period (with academic years)."""
        from models.finance import FinancialManager
        year, term = config.Config.CURRENT_ACADEMIC_YEAR, config.Config.CURRENT_TERM
        self.rollover_current_term_var.set(f"{term} ({year})")
        next_year, next_term = FinancialManager._resolve_rollover_target(year, term)
        self.rollover_next_term_var.set(next_term)
        self.rollover_next_year_var.set(next_year)
        suffix = "  - new academic year" if next_year != year else ""
        self.rollover_next_period_var.set(f"{next_term} ({next_year}){suffix}")

    def _selected_rollover_student_id(self):
        selected = self.rollover_tree.selection()
        if not selected:
            return None
        values = self.rollover_tree.item(selected[0], 'values')
        try:
            return int(values[0])
        except (TypeError, ValueError, IndexError):
            return None

    def _preview_rollover_with_current_exclusions(self):
        """Refresh preview after carry-forward inclusion changes."""
        from models.finance import FinancialManager
        to_term = self.rollover_next_term_var.get().strip() or None
        preview = FinancialManager.get_term_rollover_preview(
            academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
            from_term=config.Config.CURRENT_TERM,
            to_term=to_term,
            excluded_student_ids=self._rollover_excluded_carry_ids
        )
        self._rollover_preview = preview
        self._rollover_preview_rows = preview.get('rows') or []
        self._rollover_excluded_carry_ids = set(preview.get('excluded_carry_student_ids') or [])
        self._update_rollover_summary(preview)
        self._render_rollover_preview()
        return preview

    def toggle_selected_rollover_carry(self):
        """Toggle whether the selected student's carried balance enters the new term."""
        student_id = self._selected_rollover_student_id()
        if not student_id:
            messagebox.showwarning("Select", "Select a student from the rollover preview.")
            return
        if student_id in self._rollover_excluded_carry_ids:
            self._rollover_excluded_carry_ids.remove(student_id)
        else:
            self._rollover_excluded_carry_ids.add(student_id)
        try:
            preview = self._preview_rollover_with_current_exclusions()
            excluded_count = len(preview.get('excluded_carry_student_ids') or [])
            self.rollover_info_var.set(f"Carry-forward choices updated. Excluded students: {excluded_count}.")
        except Exception as e:
            messagebox.showerror("Preview Failed", f"Failed to update carry-forward choice: {e}")

    def include_all_rollover_carry(self):
        """Clear all manual carry-forward exclusions and refresh preview."""
        self._rollover_excluded_carry_ids = set()
        try:
            self._preview_rollover_with_current_exclusions()
            self.rollover_info_var.set("All eligible carried balances are included again.")
        except Exception as e:
            messagebox.showerror("Preview Failed", f"Failed to include all carried balances: {e}")

    def _on_rollover_tree_click(self, event):
        """Allow direct toggling from the Include Carry column."""
        region = self.rollover_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        column = self.rollover_tree.identify_column(event.x)
        row_id = self.rollover_tree.identify_row(event.y)
        if column != "#2" or not row_id:
            return
        self.rollover_tree.selection_set(row_id)
        self.rollover_tree.focus(row_id)
        self.frame.after(1, self.toggle_selected_rollover_carry)
        return "break"

    def preview_term_rollover(self):
        """Generate rollover preview using centralized backend service."""
        try:
            from models.finance import FinancialManager
            to_term = self.rollover_next_term_var.get().strip() or None
            preview = FinancialManager.get_term_rollover_preview(
                academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
                from_term=config.Config.CURRENT_TERM,
                to_term=to_term,
                excluded_student_ids=self._rollover_excluded_carry_ids
            )
            self._rollover_preview = preview
            self._rollover_preview_rows = preview.get('rows') or []
            self._rollover_excluded_carry_ids = set(preview.get('excluded_carry_student_ids') or [])
            self._update_rollover_summary(preview)
            self._render_rollover_preview()
            info_message = (
                f"Preview ready for {preview.get('from_term')} {preview.get('from_academic_year')} -> "
                f"{preview.get('to_term')} {preview.get('to_academic_year')}. Review and confirm before execution."
            )
            warnings = preview.get('warnings') or []
            if warnings:
                info_message = f"{info_message} Warning: {' '.join(warnings)}"
            self.rollover_info_var.set(info_message)
        except Exception as e:
            messagebox.showerror("Preview Failed", f"Failed to build rollover preview: {e}")

    def execute_term_rollover(self):
        """Execute rollover after explicit confirmation."""
        try:
            from models.finance import FinancialManager
            from_term = config.Config.CURRENT_TERM
            from_year = config.Config.CURRENT_ACADEMIC_YEAR
            to_year, to_term = FinancialManager._resolve_rollover_target(from_year, from_term)

            preview = getattr(self, '_rollover_preview', None)
            if (not preview or preview.get('to_term') != to_term or preview.get('from_term') != from_term
                    or preview.get('to_academic_year') != to_year):
                self.preview_term_rollover()
                preview = getattr(self, '_rollover_preview', None)
            if not preview:
                return

            summary = preview.get('summary') or {}
            excluded_count = len(self._rollover_excluded_carry_ids)
            year_note = (
                f"\n\nThis closes academic year {from_year}: the current academic year becomes {to_year} "
                f"and last year's term dates are cleared. Enter the new term dates in Preferences afterwards."
                if to_year != from_year else ""
            )
            confirm = messagebox.askyesno(
                "Confirm Term Rollover",
                f"Execute rollover from {from_term} {from_year} to {to_term} {to_year}?\n\n"
                f"Students: {summary.get('total_students', 0)}\n"
                f"Carry Forward: {summary.get('carry_students', 0)}\n"
                f"Credit Forward: {summary.get('credit_students', 0)} "
                f"({format_currency(float(summary.get('credit_carried_total', 0) or 0))})\n"
                f"Reset: {summary.get('reset_students', 0)}\n"
                f"Manual Carry Exclusions: {excluded_count}\n"
                f"Opening Balance Total: {format_currency(float(summary.get('opening_balance_total', 0) or 0))}\n\n"
                f"This will update the current term, write rollover records, and mark all new-student badges as continuing."
                f"{year_note}"
            )
            if not confirm:
                return

            result = FinancialManager.execute_term_rollover(
                academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
                from_term=from_term,
                to_term=to_term,
                term_start_date=(self.rollover_start_date_var.get().strip() or None),
                excluded_student_ids=self._rollover_excluded_carry_ids
            )
            self._rollover_preview = result
            self._rollover_preview_rows = result.get('rows') or []
            self._rollover_excluded_carry_ids = set()
            self._refresh_rollover_period_labels()
            self.rollover_start_date_var.set('')
            self._update_rollover_summary(result)
            self._render_rollover_preview()
            self.load_fee_types()
            self.load_student_balances()
            self.load_financial_summary()
            self.rollover_info_var.set(
                f"Rollover completed. Current term is now {config.Config.CURRENT_TERM} {config.Config.CURRENT_ACADEMIC_YEAR}."
            )
            cloned_fee_types = int(result.get('cloned_fee_types', 0) or 0)
            continuing_students = int(result.get('continuing_students_updated', 0) or 0)
            messagebox.showinfo(
                "Rollover Complete",
                f"Term rollover to {config.Config.CURRENT_TERM} {config.Config.CURRENT_ACADEMIC_YEAR} completed successfully."
                + (f"\n\nFee types copied from the previous term: {cloned_fee_types}" if cloned_fee_types > 0 else "")
                + (f"\n\nStudents marked as continuing: {continuing_students}" if continuing_students > 0 else "")
            )
        except Exception as e:
            messagebox.showerror("Rollover Failed", f"Failed to execute rollover: {e}")

    def show_rollover_item_details(self):
        """Show per-student rollover detail breakdown."""
        selected = self.rollover_tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Select a student from the rollover preview.")
            return
        values = self.rollover_tree.item(selected[0], 'values')
        student_id = int(values[0])
        row = next((r for r in getattr(self, '_rollover_preview_rows', []) if int(r.get('student_id') or 0) == student_id), None)
        if not row:
            messagebox.showinfo("Details", "No preview details available for the selected student.")
            return

        dialog = tk.Toplevel(self.frame)
        dialog.title(f"Rollover Details - {row.get('student_name')}")
        dialog.geometry("900x420")
        dialog.transient(self.frame)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=f"{row.get('student_name')} | Include Carry: {'Yes' if row.get('include_carry_forward', True) else 'No'} | Prev Outstanding: {format_currency(float(row.get('previous_outstanding') or 0))} | Opening Balance: {format_currency(float(row.get('opening_balance') or 0))}",
            font=('Arial', 10, 'bold')
        ).pack(anchor='w', padx=10, pady=10)

        columns = ['Source', 'Fee', 'Expected', 'Paid', 'Outstanding', 'Carry', 'Reset', 'Status']
        tree = ttk.Treeview(dialog, columns=columns, show='headings', height=14)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        tree.column('Fee', width=200)
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scroll = ttk.Scrollbar(dialog, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y', pady=10)

        for detail in row.get('details') or []:
            tree.insert('', 'end', values=(
                detail.get('source'),
                detail.get('fee_name'),
                format_currency(float(detail.get('expected_amount') or 0)),
                format_currency(float(detail.get('paid_amount') or 0)),
                format_currency(float(detail.get('outstanding') or 0)),
                format_currency(float(detail.get('carried_amount') or 0)),
                format_currency(float(detail.get('reset_amount') or 0)),
                'Reset (Excluded)' if detail.get('carry_excluded') else detail.get('status')
            ))

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
        header_frame = ttk.LabelFrame(self.expenses_frame, text="Expense Term View", padding=10)
        header_frame.pack(fill='x', padx=10, pady=(10, 0))
        self.expenses_term_info_var = tk.StringVar()
        ttk.Label(header_frame, textvariable=self.expenses_term_info_var, font=('Arial', 11, 'bold')).pack(side='left', padx=5)
        ttk.Button(header_frame, text="Previous Term", command=lambda: self._step_finance_term(-1)).pack(side='right', padx=4)
        ttk.Button(header_frame, text="Next Term", command=lambda: self._step_finance_term(1)).pack(side='right', padx=4)
        ttk.Combobox(
            header_frame,
            textvariable=self.finance_view_term_var,
            values=getattr(config.Config, 'TERMS', ['Term 1', 'Term 2', 'Term 3']),
            state='readonly',
            width=16
        ).pack(side='right', padx=4)
        ttk.Label(header_frame, text="Term:").pack(side='right', padx=(10, 4))

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
                methods = ['Cash', 'Mobile money', 'Bank Transfer', 'Check', 'Other']
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
        
        ttk.Label(summary_frame, text="Term Total:").pack(side='left', padx=5)
        self.month_expense_var = tk.StringVar(value=format_currency(0.0))
        ttk.Label(summary_frame, textvariable=self.month_expense_var, font=('Arial', 12, 'bold')).pack(side='left', padx=5)
        
        ttk.Button(summary_frame, text="Refresh", command=self.load_recent_expenses).pack(side='right', padx=5)
        # Setup right-click context menu for expenses
        self.setup_expenses_context_menu()
    
    def setup_financial_summary_tab(self):
        """Setup financial summary tab"""
        header_frame = ttk.LabelFrame(self.financial_summary_frame, text="Financial Summary Term View", padding=10)
        header_frame.pack(fill='x', padx=20, pady=(20, 0))
        self.summary_term_info_var = tk.StringVar()
        ttk.Label(header_frame, textvariable=self.summary_term_info_var, font=('Arial', 11, 'bold')).pack(side='left', padx=5)
        ttk.Button(header_frame, text="Previous Term", command=lambda: self._step_finance_term(-1)).pack(side='right', padx=4)
        ttk.Button(header_frame, text="Next Term", command=lambda: self._step_finance_term(1)).pack(side='right', padx=4)
        ttk.Combobox(
            header_frame,
            textvariable=self.finance_view_term_var,
            values=getattr(config.Config, 'TERMS', ['Term 1', 'Term 2', 'Term 3']),
            state='readonly',
            width=16
        ).pack(side='right', padx=4)
        ttk.Label(header_frame, text="Term:").pack(side='right', padx=(10, 4))

        scroll_container = ttk.Frame(self.financial_summary_frame)
        scroll_container.pack(fill='both', expand=True)

        summary_canvas = tk.Canvas(scroll_container, highlightthickness=0)
        page_scrollbar = ttk.Scrollbar(scroll_container, orient='vertical', command=summary_canvas.yview)
        summary_canvas.configure(yscrollcommand=page_scrollbar.set)
        summary_canvas.pack(side='left', fill='both', expand=True)
        page_scrollbar.pack(side='right', fill='y')

        content_frame = ttk.Frame(summary_canvas)
        content_window = summary_canvas.create_window((0, 0), window=content_frame, anchor='nw')

        def _update_scroll_region(event=None):
            summary_canvas.configure(scrollregion=summary_canvas.bbox('all'))

        def _resize_content(event):
            summary_canvas.itemconfigure(content_window, width=event.width)

        def _on_mousewheel(event):
            summary_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def _bind_mousewheel(event=None):
            summary_canvas.bind_all('<MouseWheel>', _on_mousewheel)

        def _unbind_mousewheel(event=None):
            summary_canvas.unbind_all('<MouseWheel>')

        content_frame.bind('<Configure>', _update_scroll_region)
        summary_canvas.bind('<Configure>', _resize_content)
        summary_canvas.bind('<Enter>', _bind_mousewheel)
        summary_canvas.bind('<Leave>', _unbind_mousewheel)

        # Summary cards
        summary_frame = ttk.Frame(content_frame)
        summary_frame.pack(fill='x', padx=20, pady=20)
        
        self.summary_cards = []
        summaries = [
            ('Selected Term Income', 'total_income_var', '#4CAF50'),
            ('Selected Term Expenses', 'total_expenses_var', '#F44336'),
            ('Selected Term Net', 'net_balance_var', '#2196F3'),
            ('Academic Year Income', 'academic_year_income_var', '#FF9800'),
            ('Academic Year Expenses', 'academic_year_expenses_var', '#9C27B0'),
            ('Academic Year Net', 'academic_year_net_var', '#607D8B'),
            ('Outstanding', 'outstanding_var', '#607D8B')
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
        charts_frame = ttk.LabelFrame(content_frame, text="Financial Charts", padding=10)
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
        fee_totals_frame = ttk.LabelFrame(content_frame, text="Fees Collected by Type", padding=10)
        fee_totals_frame.pack(fill='both', padx=20, pady=(0, 10))

        self.fee_totals_tree = ttk.Treeview(
            fee_totals_frame,
            columns=('Fee Type', 'Configured Terms', 'Selected Term', 'Academic Year', 'Payments'),
            show='headings',
            height=8
        )
        for col, w in (
            ('Fee Type', 220),
            ('Configured Terms', 140),
            ('Selected Term', 130),
            ('Academic Year', 130),
            ('Payments', 90)
        ):
            self.fee_totals_tree.heading(col, text=col)
            self.fee_totals_tree.column(col, width=w)

        fee_totals_scroll = ttk.Scrollbar(fee_totals_frame, orient='vertical', command=self.fee_totals_tree.yview)
        self.fee_totals_tree.configure(yscrollcommand=fee_totals_scroll.set)
        self.fee_totals_tree.pack(side='left', fill='both', expand=True)
        fee_totals_scroll.pack(side='right', fill='y')
        
        # Action buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill='x', padx=20, pady=10)
        
        actions = [
            ("Generate Report", self.generate_financial_report),
            ("Export to Excel", self.export_financial_data),
            ("Print Summary", self.print_financial_summary),
            ("Refresh Data", self.load_financial_summary)
        ]
        
        for text, command in actions:
            ttk.Button(button_frame, text=text, command=command).pack(side='left', padx=5)

    def setup_staff_salaries_tab(self):
        """Setup staff salaries tab for managing teacher salaries and advances"""
        # Top frame for filters
        top_frame = ttk.Frame(self.staff_salaries_frame)
        top_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(top_frame, text="Teacher:").pack(side='left', padx=5)
        self.staff_teacher_var = tk.StringVar()
        self.staff_teacher_combo = ttk.Combobox(top_frame, textvariable=self.staff_teacher_var, state='readonly', width=30)
        self.staff_teacher_combo.pack(side='left', padx=5)
        self.staff_teacher_combo.bind('<<ComboboxSelected>>', self.on_staff_teacher_selected)
        
        ttk.Label(top_frame, text="Status:").pack(side='left', padx=5)
        self.staff_status_var = tk.StringVar(value="All")
        status_vals = ['All', 'Pending', 'Approved', 'Deducted']
        self.staff_status_combo = ttk.Combobox(top_frame, textvariable=self.staff_status_var, values=status_vals, state='readonly', width=12)
        self.staff_status_combo.pack(side='left', padx=5)
        self.staff_status_combo.bind('<<ComboboxSelected>>', lambda e: self.load_staff_salaries())

        ttk.Label(top_frame, text="Month:").pack(side='left', padx=(10, 5))
        self.salary_month_var = tk.StringVar(value=date.today().strftime('%Y-%m'))
        self.salary_month_combo = ttk.Combobox(
            top_frame,
            textvariable=self.salary_month_var,
            values=self._get_salary_month_options(),
            state='readonly',
            width=10
        )
        self.salary_month_combo.pack(side='left', padx=5)
        self.salary_month_combo.bind('<<ComboboxSelected>>', lambda e: self.load_staff_salaries())

        # Salary totals summary
        self.total_salary_only_var = tk.StringVar(value="---")
        self.total_salary_with_allowances_var = tk.StringVar(value="---")
        self.total_salary_net_var = tk.StringVar(value="---")
        ttk.Label(top_frame, text="Salaries Only:").pack(side='left', padx=(20, 5))
        ttk.Label(top_frame, textvariable=self.total_salary_only_var, font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        ttk.Label(top_frame, text="Salaries + Allowances:").pack(side='left', padx=(20, 5))
        ttk.Label(top_frame, textvariable=self.total_salary_with_allowances_var, font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        ttk.Label(top_frame, text="Net Payable:").pack(side='left', padx=(20, 5))
        ttk.Label(top_frame, textvariable=self.total_salary_net_var, font=('Arial', 10, 'bold')).pack(side='left', padx=5)

        ttk.Button(top_frame, text="Refresh", command=self.load_staff_salaries).pack(side='right', padx=5)
        
        # Left frame: Teacher salary info
        left_frame = ttk.Frame(self.staff_salaries_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # Teacher salary details
        info_frame = ttk.LabelFrame(left_frame, text="Teacher Salary Information", padding=10)
        info_frame.pack(fill='x', pady=(0, 10))
        
        info_fields = [
            ("Teacher Code:", "staff_code_var"),
            ("Teacher Name:", "staff_name_var"),
            ("Base Salary:", "staff_salary_var"),
            ("Allowance:", "staff_allowance_var"),
            ("Total Advances:", "staff_advances_var"),
            ("Net Salary:", "staff_net_var"),
            ("Status:", "staff_salary_status_var")
        ]
        
        for label_text, var_name in info_fields:
            row = ttk.Frame(info_frame)
            row.pack(fill='x', pady=5)
            ttk.Label(row, text=label_text, width=15).pack(side='left')
            setattr(self, var_name, tk.StringVar(value="---"))
            ttk.Label(row, textvariable=getattr(self, var_name), font=('Arial', 10, 'bold')).pack(side='left', padx=10)

        # Monthly salary payment status (per selected month)
        paid_row = ttk.Frame(info_frame)
        paid_row.pack(fill='x', pady=8)
        self.salary_paid_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            paid_row,
            text="Salary Paid (selected month)",
            variable=self.salary_paid_var
        ).pack(side='left')
        ttk.Button(
            paid_row,
            text="Update Paid Status",
            command=self.update_salary_paid_status
        ).pack(side='left', padx=10)
        
        # Record advance form
        advance_frame = ttk.LabelFrame(left_frame, text="Record Salary Advance", padding=15)
        advance_frame.pack(fill='x')
        
        ttk.Label(advance_frame, text="Advance Amount:").grid(row=0, column=0, sticky='w', pady=5)
        self.advance_amount_var = tk.StringVar()
        ttk.Entry(advance_frame, textvariable=self.advance_amount_var, width=25).grid(row=0, column=1, sticky='w', pady=5, padx=5)
        
        ttk.Label(advance_frame, text="Description:").grid(row=1, column=0, sticky='w', pady=5)
        self.advance_desc_var = tk.StringVar()
        ttk.Entry(advance_frame, textvariable=self.advance_desc_var, width=25).grid(row=1, column=1, sticky='w', pady=5, padx=5)
        
        ttk.Label(advance_frame, text="Date:").grid(row=2, column=0, sticky='w', pady=5)
        self.advance_date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        ttk.Entry(advance_frame, textvariable=self.advance_date_var, width=25).grid(row=2, column=1, sticky='w', pady=5, padx=5)
        
        ttk.Label(advance_frame, text="Status:").grid(row=3, column=0, sticky='w', pady=5)
        self.advance_status_var = tk.StringVar(value="Pending")
        status_opts = ['Pending', 'Approved', 'Deducted']
        ttk.Combobox(advance_frame, textvariable=self.advance_status_var, values=status_opts, state='readonly', width=23).grid(row=3, column=1, sticky='w', pady=5, padx=5)
        
        btn_frame = ttk.Frame(advance_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="Record Advance", command=self.record_salary_advance).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_advance_form).pack(side='left', padx=5)

        # Allowance update form
        allowance_frame = ttk.LabelFrame(left_frame, text="Set Allowance", padding=15)
        allowance_frame.pack(fill='x', pady=(10, 0))

        ttk.Label(allowance_frame, text="Allowance Amount:").grid(row=0, column=0, sticky='w', pady=5)
        self.allowance_amount_var = tk.StringVar()
        ttk.Entry(allowance_frame, textvariable=self.allowance_amount_var, width=25).grid(row=0, column=1, sticky='w', pady=5, padx=5)

        allowance_btns = ttk.Frame(allowance_frame)
        allowance_btns.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(allowance_btns, text="Save Allowance", command=self.save_allowance).pack(side='left', padx=5)
        ttk.Button(allowance_btns, text="Clear", command=self.clear_allowance_form).pack(side='left', padx=5)
        
        # Right frame: Advances list
        right_frame = ttk.Frame(self.staff_salaries_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        
        # Advances table
        table_frame = ttk.LabelFrame(right_frame, text="Salary Advances", padding=10)
        table_frame.pack(fill='both', expand=True)
        
        columns = ['ID', 'Teacher', 'Amount', 'Date', 'Description', 'Status']
        self.advances_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=20
        )
        
        for col in columns:
            self.advances_tree.heading(col, text=col)
            self.advances_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.advances_tree.yview)
        self.advances_tree.configure(yscrollcommand=scrollbar.set)
        
        self.advances_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Action buttons for advances
        action_frame = ttk.Frame(right_frame)
        action_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(action_frame, text="Edit Selected", command=self.edit_salary_advance).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Delete Selected", command=self.delete_salary_advance).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Refresh", command=self.load_staff_salaries).pack(side='right', padx=5)

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

        self.fee_types_tree = ttk.Treeview(left, columns=('ID', 'Name', 'Amount', 'Term', 'Required', 'Classes'), show='headings', height=12)
        for col in ('ID', 'Name', 'Amount', 'Term', 'Required', 'Classes'):
            self.fee_types_tree.heading(col, text=col)
            width = 220 if col == 'Classes' else 100
            self.fee_types_tree.column(col, width=width)
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
            # Build fee_type_id -> "Class1, Class2" map for current academic year.
            class_scope_map = {}
            try:
                scope_rows = db.execute_query(
                    f"""
                    SELECT
                        ftc.fee_type_id,
                        {db.group_concat_distinct("c.class_name", "', '")} AS classes
                    FROM fee_type_classes ftc
                    JOIN classes c ON c.class_id = ftc.class_id
                    WHERE (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                    GROUP BY ftc.fee_type_id
                    """,
                    (config.Config.CURRENT_ACADEMIC_YEAR,),
                    fetch=True
                ) or []
                class_scope_map = {int(r['fee_type_id']): (r.get('classes') or '') for r in scope_rows}
            except Exception:
                class_scope_map = {}

            for ft in fee_types:
                class_scope = class_scope_map.get(int(ft.fee_type_id), '')
                scope_text = class_scope if class_scope else 'All'
                self.fee_types_tree.insert(
                    '',
                    'end',
                    values=(
                        ft.fee_type_id,
                        ft.fee_name,
                        format_currency(ft.amount),
                        ft.term,
                        'Yes' if ft.is_required else 'No',
                        scope_text
                    )
                )
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
            normalized_term = config.Config.normalize_term_name(data['term'])
            query = "INSERT INTO fee_types (fee_name, description, amount, term, academic_year, is_required) VALUES (%s, %s, %s, %s, %s, %s)"
            fid = db.execute_query(query, (data['fee_name'], '', data['amount'], normalized_term, config.Config.CURRENT_ACADEMIC_YEAR, 1 if data['is_required'] else 0))
            # Persist mappings if specific classes chosen
            if not data.get('apply_to_all'):
                # handle numeric ids
                for cid in data.get('class_ids', []) or []:
                    try:
                        db.execute_query("INSERT IGNORE INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s, %s, %s)", (fid, cid, config.Config.CURRENT_ACADEMIC_YEAR))
                    except Exception:
                        pass

                # handle class names (these may come from students.class fallback)
                for cname in data.get('class_names', []) or []:
                    try:
                        # try to find class id by name
                        found = db.execute_query('SELECT class_id FROM classes WHERE class_name=%s', (cname,), fetch=True)
                        if found and len(found) > 0:
                            cid = found[0]['class_id']
                        else:
                            # create a classes row for this name so we can reference it
                            cid = db.execute_query('INSERT INTO classes (class_name, academic_year) VALUES (%s, %s)', (cname, config.Config.CURRENT_ACADEMIC_YEAR))
                        if cid:
                            try:
                                db.execute_query("INSERT IGNORE INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s, %s, %s)", (fid, cid, config.Config.CURRENT_ACADEMIC_YEAR))
                            except Exception:
                                pass
                    except Exception:
                        pass
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

        # fetch existing class mappings
        try:
            mappings = db.execute_query('SELECT class_id FROM fee_type_classes WHERE fee_type_id=%s', (fid,), fetch=True)
            existing_class_ids = [r['class_id'] for r in mappings] if mappings else []
        except Exception:
            existing_class_ids = []

        existing['class_ids'] = existing_class_ids
        dialog = FeeTypeDialog(self.frame, title='Edit Fee Type', fee_type=existing)
        dialog.show()
        if not dialog.result:
            return
        data = dialog.result_data
        try:
            normalized_term = config.Config.normalize_term_name(data['term'])
            query = "UPDATE fee_types SET fee_name=%s, amount=%s, term=%s, is_required=%s WHERE fee_type_id=%s"
            db.execute_query(query, (data['fee_name'], data['amount'], normalized_term, 1 if data.get('is_required') else 0, fid))
            # Update mappings: remove old then insert new if needed
            try:
                db.execute_query('DELETE FROM fee_type_classes WHERE fee_type_id=%s', (fid,))
                if not data.get('apply_to_all'):
                    for cid in data.get('class_ids', []) or []:
                        try:
                            db.execute_query("INSERT IGNORE INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s, %s, %s)", (fid, cid, config.Config.CURRENT_ACADEMIC_YEAR))
                        except Exception:
                            pass
                    for cname in data.get('class_names', []) or []:
                        try:
                            found = db.execute_query('SELECT class_id FROM classes WHERE class_name=%s', (cname,), fetch=True)
                            if found and len(found) > 0:
                                cid = found[0]['class_id']
                            else:
                                cid = db.execute_query('INSERT INTO classes (class_name, academic_year) VALUES (%s, %s)', (cname, config.Config.CURRENT_ACADEMIC_YEAR))
                            if cid:
                                try:
                                    db.execute_query("INSERT IGNORE INTO fee_type_classes (fee_type_id, class_id, academic_year) VALUES (%s, %s, %s)", (fid, cid, config.Config.CURRENT_ACADEMIC_YEAR))
                                except Exception:
                                    pass
                        except Exception:
                            pass
            except Exception:
                pass
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
        self.reset_finance_view()
        self.load_students_for_payment()
        self.load_fee_types()
        self.load_recent_payments()
        self.load_classes_for_filter()
        self.load_student_balances()
        self.load_term_rollover_data()
        self.load_recent_expenses()
        self.load_financial_summary()
        self.load_staff_salaries()

    def refresh_data(self):
        """Refresh finance tab content after application-wide changes."""
        self.load_data()
    
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
            # also populate filter student combo
            self.filter_student_combo['values'] = [''] + student_list
        except Exception as e:
            print(f"Error loading students: {e}")
    
    def _extract_selected_student_class(self) -> str:
        """Extract class name from student combobox selection text."""
        try:
            student_sel = (self.student_var.get() or '').strip()
            m = re.search(r"\(([^)]+)\)", student_sel)
            if m:
                return m.group(1).strip()
        except Exception:
            pass
        return ""

    def on_student_selected(self, event=None):
        """Reload fee types based on selected student's class."""
        try:
            previous_fee_type_id = self._selected_fee_type_id()
            class_name = self._extract_selected_student_class()
            self.load_fee_types(class_name=class_name)
            if previous_fee_type_id:
                for option in self.fee_type_combo['values'] or []:
                    if str(option).startswith(f"{previous_fee_type_id}:"):
                        self.fee_type_var.set(option)
                        self.on_fee_type_selected()
                        return
            # reset selected fee type if it is no longer valid
            current = (self.fee_type_var.get() or '').strip()
            if current and current not in (self.fee_type_combo['values'] or []):
                self.fee_type_var.set('')
                self.amount_var.set('')
            elif current:
                self.on_fee_type_selected()
        except Exception:
            pass

    def _extract_selected_student_id(self) -> int:
        """Extract the selected student id from the payment student field."""
        student_sel = (self.student_var.get() or '').strip()
        try:
            return int(student_sel.split(':')[0])
        except (ValueError, IndexError):
            return 0

    def _selected_fee_type_id(self) -> int:
        """Extract the selected fee type id from the payment fee field."""
        try:
            return int((self.fee_type_var.get() or '').split(':')[0])
        except (ValueError, IndexError):
            return 0

    def _load_student_carried_forward_amount(self, student_id: int) -> float:
        """Return this student's remaining carried-forward balance for the active term."""
        if not student_id:
            return 0.0
        try:
            from models.finance import FinancialManager
            balance = FinancialManager.get_student_balance(
                student_id=student_id,
                academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
                term=config.Config.CURRENT_TERM
            )
            return float(balance.get('remaining_carried_balance') or balance.get('carried_balance') or 0)
        except Exception:
            return 0.0

    def load_fee_types(self, class_name: str = ""):
        """Load fee types for combobox (optionally filtered by student class)."""
        try:
            from models.finance import FeeType
            FeeType.ensure_carried_forward_fee_type(config.Config.CURRENT_ACADEMIC_YEAR, config.Config.CURRENT_TERM)
            selected_student_id = self._extract_selected_student_id()

            def format_fee_option(fee_type_id, fee_name, amount):
                display_amount = float(amount or 0)
                if FeeType.is_carried_forward_fee_name(fee_name):
                    display_amount = self._load_student_carried_forward_amount(selected_student_id)
                return f"{fee_type_id}: {fee_name} ({format_currency(display_amount)})"

            if class_name:
                fee_types = FeeType.get_applicable_for_class(
                    class_name,
                    config.Config.CURRENT_ACADEMIC_YEAR,
                    config.Config.CURRENT_TERM
                )
                fee_list = [format_fee_option(ft.fee_type_id, ft.fee_name, ft.amount) for ft in fee_types]
            else:
                query = """
                    SELECT fee_type_id, fee_name, amount
                    FROM fee_types
                    WHERE academic_year = %s
                      AND (
                            term = %s
                            OR term IS NULL
                            OR term = ''
                            OR NOT EXISTS (
                                SELECT 1
                                FROM fee_types ftx
                                WHERE ftx.academic_year = %s
                                  AND ftx.term = %s
                            )
                      )
                    ORDER BY fee_name
                """
                results = db.execute_query(
                    query,
                    (
                        config.Config.CURRENT_ACADEMIC_YEAR,
                        config.Config.CURRENT_TERM,
                        config.Config.CURRENT_ACADEMIC_YEAR,
                        config.Config.CURRENT_TERM
                    ),
                    fetch=True
                )
                fee_list = [format_fee_option(r['fee_type_id'], r['fee_name'], r['amount']) for r in results]
            self.fee_type_combo['values'] = fee_list
            # Keep filter combos global; only payment form list should be class-scoped.
            if not class_name:
                try:
                    self.filter_fee_combo['values'] = [''] + fee_list
                except Exception:
                    pass
                try:
                    self.balance_fee_combo['values'] = [''] + fee_list
                except Exception:
                    pass
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
            from models.finance import FeeType

            if FeeType.is_carried_forward_fee_name(fee_name):
                student_id = self._extract_selected_student_id()
                expected = self._load_student_carried_forward_amount(student_id)
                self.amount_var.set(str(int(expected) if float(expected).is_integer() else f"{expected:.2f}"))
                if hasattr(self, 'amount_entry'):
                    self.amount_entry.config(state='normal')
                return

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
        """Load fee payments (recent or all, depending on filter)"""
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
            
            # Get recent payments (apply optional filters from filter controls)
            fee_filter = None
            student_filter = None
            # Parse selected fee id from filter combobox (format: "<id>: <name> (...)" )
            try:
                fsel = (self.filter_fee_var.get() or '').strip()
                if fsel and ':' in fsel:
                    fee_filter = int(fsel.split(':', 1)[0])
            except Exception:
                fee_filter = None
            # Parse selected student id (format: "<id>: ...") or fallback to name/code search
            ssel = (self.filter_student_var.get() or '').strip()
            try:
                if ssel and ':' in ssel:
                    student_filter = int(ssel.split(':', 1)[0])
            except Exception:
                student_filter = None

            where_clauses = []
            params = []
            if fee_filter:
                where_clauses.append('sf.fee_type_id = %s')
                params.append(fee_filter)
            if student_filter:
                where_clauses.append('sf.student_id = %s')
                params.append(student_filter)
            elif ssel:
                where_clauses.append('(CONCAT(s.first_name, \" \", s.last_name) LIKE %s OR s.student_code LIKE %s)')
                params.append(f"%{ssel}%")
                params.append(f"%{ssel}%")

            where_sql = ''
            if where_clauses:
                where_sql = 'WHERE ' + ' AND '.join(where_clauses)

            limit_clause = ""
            if not getattr(self, 'show_all_payments_var', None) or not self.show_all_payments_var.get():
                limit_clause = "LIMIT 200"

            query = f"""
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
                {where_sql}
                ORDER BY sf.payment_date DESC, sf.created_at DESC
                {limit_clause}
            """
            params_tuple = tuple(params) if params else None
            # Defensive check: ensure number of %s placeholders matches params provided
            try:
                placeholder_count = query.count('%s')
                if params_tuple is not None and placeholder_count != len(params_tuple):
                    print(f"Warning: placeholder count ({placeholder_count}) != params provided ({len(params_tuple)})")
                    print('Query:', query)
                    print('Params before adjust:', params_tuple)
                    if placeholder_count == 0:
                        params_tuple = None
                    elif placeholder_count < len(params_tuple):
                        params_tuple = params_tuple[:placeholder_count]
                    else:
                        # pad with None
                        params_tuple = tuple(list(params_tuple) + [None] * (placeholder_count - len(params_tuple)))

                results = db.execute_query(query, params_tuple, fetch=True)
            except Exception as e:
                print('Error executing payments query:', e)
                print('Query:', query)
                print('Params used:', params_tuple)
                raise
            
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

    def search_payments(self):
        """Handler for Search button to reload payments using current filters"""
        try:
            self.load_recent_payments()
        except Exception as e:
            print(f"Error searching payments: {e}")
    
    def load_student_balances(self):
        """Load student balances (supports fee-type filtering)"""
        # Clear existing items
        for item in self.balances_tree.get_children():
            self.balances_tree.delete(item)

        try:
            # Determine fee type filter if selected
            fee_sel = getattr(self, 'balance_fee_var', None)
            fee_type_id = None
            if fee_sel:
                sel = self.balance_fee_var.get() or ''
                if sel:
                    try:
                        fee_type_id = int(sel.split(':')[0])
                    except Exception:
                        fee_type_id = None

            # Use FinancialManager to get balances (backend now supports fee_type filter)
            from models.finance import FinancialManager
            results = FinancialManager.get_student_balances(config.Config.CURRENT_ACADEMIC_YEAR, fee_type_id=fee_type_id)

            total_outstanding = 0
            with_balance = 0
            fully_paid = 0

            # Apply client-side filters (class, status, search)
            class_filter = self.balance_class_var.get()
            status_filter = self.balance_status_var.get()
            search_term = (self.balance_search_var.get() or '').strip().lower()

            for row in results:
                # Apply class filter
                if class_filter and class_filter != 'All' and row.get('class') != class_filter:
                    continue
                balance = float(row.get('balance') or 0)
                paid = float(row.get('amount_paid') or 0)
                total_fees = float(row.get('opening_balance') or 0)
                status = "Paid" if balance <= 0 else "Partial" if paid > 0 else "Unpaid"
                if float(row.get('carried_balance') or 0) > 0 and balance > 0:
                    status = "Carried Forward"

                # Apply status filter
                if status_filter and status_filter != 'All' and status != status_filter:
                    continue

                # Apply search
                if search_term:
                    if search_term not in (row.get('student_name', '') or '').lower():
                        continue

                if balance > 0:
                    total_outstanding += balance
                    with_balance += 1
                else:
                    fully_paid += 1

                self.balances_tree.insert('', 'end', values=(
                    row.get('student_id'),
                    row.get('student_name'),
                    row.get('class'),
                    format_currency(total_fees),
                    format_currency(paid),
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
        """Handler for search button - reuse load_student_balances so fee-type filter is honored"""
        try:
            self.load_student_balances()
        except Exception as e:
            print(f"Error searching balances: {e}")
    
    def load_recent_expenses(self):
        """Load recent expenses"""
        # Clear existing items
        for item in self.expenses_tree.get_children():
            self.expenses_tree.delete(item)
        
        try:
            from models.finance import Expense

            academic_year, term = self._current_finance_view()
            total = Expense.get_term_expense_total(academic_year, term)
            self.month_expense_var.set(format_currency(total))

            results = Expense.get_term_expenses(academic_year, term, limit=50)
            for expense in results:
                self.expenses_tree.insert('', 'end', values=(
                    expense.expense_id,
                    expense.expense_date,
                    expense.description[:50] + "..." if len(expense.description) > 50 else expense.description,
                    expense.category or 'Uncategorized',
                    format_currency(float(expense.amount or 0)),
                    expense.payment_method,
                    expense.receipt_number or ''
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
            from models.finance import Expense
            Expense.ensure_term_columns()
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
            ttk.Combobox(dlg, textvariable=method_var, values=['Cash','Mobile money','Bank Transfer','Check','Other'], state='readonly', width=20).grid(row=4, column=1, padx=6, pady=4, sticky='w')

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
                    academic_year, term = self._current_finance_view()

                    db.execute_query(
                        """UPDATE expenses
                           SET expense_date=%s, description=%s, category=%s, academic_year=%s, term=%s,
                               amount=%s, payment_method=%s, receipt_number=%s
                           WHERE expense_id=%s""",
                        (pdate, desc, cat, academic_year, term, amt, mth, rno, expense_id)
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
            from models.finance import FinancialManager

            academic_year, term = self._current_finance_view()
            summary = FinancialManager.get_term_financial_summary(academic_year, term)

            self.total_income_var.set(format_currency(float(summary.get('total_income') or 0)))
            self.total_expenses_var.set(format_currency(float(summary.get('total_expenses') or 0)))
            self.net_balance_var.set(format_currency(float(summary.get('net_balance') or 0)))
            self.academic_year_income_var.set(format_currency(float(summary.get('academic_year_total_income') or 0)))
            self.academic_year_expenses_var.set(format_currency(float(summary.get('academic_year_total_expenses') or 0)))
            self.academic_year_net_var.set(format_currency(float(summary.get('academic_year_net_balance') or 0)))
            self.outstanding_var.set(format_currency(float(summary.get('outstanding_fees') or 0)))

            self.load_monthly_breakdown(summary.get('monthly_breakdown') or [])
            self.load_expense_categories(summary.get('expense_categories') or [])

            for item in self.fee_totals_tree.get_children():
                self.fee_totals_tree.delete(item)
            for row in summary.get('fee_totals') or []:
                self.fee_totals_tree.insert('', 'end', values=(
                    row.get('fee_name'),
                    row.get('fee_terms') or '',
                    format_currency(float(row.get('term_collected', 0) or 0)),
                    format_currency(float(row.get('academic_year_collected', 0) or 0)),
                    row.get('term_payment_count', 0)
                ))
            
        except Exception as e:
            print(f"Error loading financial summary: {e}")
    
    def load_monthly_breakdown(self, rows=None):
        """Load monthly financial breakdown"""
        # Clear existing items
        for item in self.monthly_tree.get_children():
            self.monthly_tree.delete(item)
        
        try:
            for row in rows or []:
                self.monthly_tree.insert('', 'end', values=(
                    row.get('month'),
                    format_currency(float(row.get('income') or 0)),
                    format_currency(float(row.get('expenses') or 0)),
                    format_currency(float(row.get('net') or 0))
                ))
                
        except Exception as e:
            print(f"Error loading monthly breakdown: {e}")
    
    def load_expense_categories(self, rows=None):
        """Load expense categories breakdown"""
        # Clear existing items
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        
        try:
            for row in rows or []:
                self.category_tree.insert('', 'end', values=(
                    row['category'],
                    row.get('expense_count') or row.get('count') or 0,
                    format_currency(float(row.get('total_amount') or row.get('total') or 0))
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

            # Enforce fee type applicability to selected student's class
            try:
                class_name = self._extract_selected_student_class()
                if not class_name:
                    qclass = "SELECT class FROM students WHERE student_id=%s"
                    cres = db.execute_query(qclass, (student_id,), fetch=True)
                    class_name = (cres[0].get('class') if cres else '') or ''
                from models.finance import FeeType
                if not FeeType.is_applicable_to_class(fee_type_id, class_name, config.Config.CURRENT_ACADEMIC_YEAR):
                    messagebox.showerror(
                        "Error",
                        f"This fee type does not apply to class '{class_name}'."
                    )
                    return
            except Exception:
                # Do not block payment on validation lookup failures
                pass
            
            # Get description
            description = self.description_text.get("1.0", "end-1c").strip()
            
            # Save via model to enforce exemption rules and receipt sequencing
            from models.finance import FeePayment
            receipt_number = self.receipt_var.get().strip()
            payment = FeePayment(
                student_id=student_id,
                fee_type_id=fee_type_id,
                amount_paid=amount,
                payment_date=self.date_var.get(),
                payment_method=self.payment_method_var.get(),
                receipt_number=receipt_number,
                description=description
            )
            success, msg = payment.save()
            if not success:
                messagebox.showerror("Error", msg)
                return

            # Update receipt if generated
            if payment.receipt_number:
                self.receipt_var.set(payment.receipt_number)
            messagebox.showinfo("Success", msg)
            
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
        if hasattr(self, 'amount_entry'):
            self.amount_entry.config(state='normal')
    
    def record_expense(self):
        """Record an expense"""
        try:
            from models.finance import Expense
            Expense.ensure_term_columns()
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
                (expense_date, description, category, academic_year, term, amount, payment_method, receipt_number, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            academic_year, term = self._current_finance_view()
            params = (
                self.expense_date_var.get(),
                self.expense_desc_var.get(),
                self.expense_category_var.get() or 'Other',
                academic_year,
                term,
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
            
            from models.student import StudentManager
            summary = StudentManager.get_student_financial_summary(student_id)
            
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
            
            payment_history = summary.get('payment_history') or []
            last_payment_map = {}
            for payment in payment_history:
                fee_name = payment.get('fee_name') or ''
                payment_date = payment.get('payment_date')
                if payment_date:
                    last_payment_map[fee_name] = str(payment_date)

            total_expected = total_paid = total_balance = 0
            for row in summary.get('fee_details', []):
                fee_name = row.get('fee_name') or ''
                expected_amt = float(row.get('expected_amount') or 0)
                paid_amt = float(row.get('paid_amount') or 0)
                balance_val = float(row.get('balance') or 0)
                tree.insert('', 'end', values=(
                    fee_name,
                    format_currency(expected_amt),
                    format_currency(paid_amt),
                    format_currency(balance_val),
                    last_payment_map.get(fee_name, 'Opening Balance' if fee_name == 'Carried Forward Fee Balance' else 'None')
                ))
                total_expected += expected_amt
                total_paid += paid_amt
                total_balance += balance_val
            
            # Add totals row
            tree.insert('', 'end', values=(
                'TOTAL',
                format_currency(float(summary.get('total_due') or total_expected)),
                format_currency(float(summary.get('total_paid') or total_paid)),
                format_currency(float(summary.get('balance') or total_balance)),
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
        """Show payment history for student (supports fee-type filtering)"""
        try:
            dialog = tk.Toplevel(self.frame)
            dialog.title(f"Payment History - {student_name}")
            dialog.geometry("700x450")

            # Top controls: Fee type filter + filtered balance display
            top_ctrl = ttk.Frame(dialog)
            top_ctrl.pack(fill='x', padx=10, pady=5)

            ttk.Label(top_ctrl, text='Filter by Fee Type:').pack(side='left', padx=(0,6))
            fee_var = tk.StringVar(value='')
            fee_combo = ttk.Combobox(top_ctrl, textvariable=fee_var, width=35)
            fee_combo.pack(side='left', padx=(0,6))

            # balance label
            filtered_balance_var = tk.StringVar(value='')
            ttk.Label(top_ctrl, textvariable=filtered_balance_var, font=('Arial', 10, 'bold')).pack(side='right')

            # Populate fee types
            try:
                q = "SELECT fee_type_id, fee_name, amount FROM fee_types WHERE academic_year=%s ORDER BY fee_name"
                fee_results = db.execute_query(q, (config.Config.CURRENT_ACADEMIC_YEAR,), fetch=True)
                fee_list = [''] + [f"{r['fee_type_id']}: {r['fee_name']} ({format_currency(r['amount'])})" for r in fee_results]
                fee_combo['values'] = fee_list
            except Exception:
                fee_combo['values'] = ['']

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

            # Summary
            summary_frame = ttk.Frame(dialog)
            summary_frame.pack(fill='x', padx=10, pady=5)
            summary_var = tk.StringVar(value="Total Payments: ")
            summary_label = ttk.Label(summary_frame, textvariable=summary_var, font=('Arial', 10, 'bold'))
            summary_label.pack()

            # Function to reload payments based on selected fee type
            def reload_payments():
                # clear
                for it in tree.get_children():
                    tree.delete(it)

                sel = fee_var.get() or ''
                fee_type_id = None
                if sel:
                    try:
                        fee_type_id = int(sel.split(':')[0])
                    except Exception:
                        fee_type_id = None

                # Build query
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
                """
                params = [student_id]
                if fee_type_id:
                    query += " AND ft.fee_type_id = %s"
                    params.append(fee_type_id)
                query += " ORDER BY sf.payment_date DESC"

                rows = db.execute_query(query, tuple(params), fetch=True)
                total = 0
                for row in rows:
                    tree.insert('', 'end', values=(
                        row['payment_date'],
                        row['fee_name'],
                        format_currency(float(row['amount_paid'])),
                        row['payment_method'],
                        row['receipt_number'] or '',
                        row['description'] or ''
                    ))
                    total += float(row['amount_paid'])

                # Update filtered balance using backend helper
                try:
                    from models.finance import FinancialManager
                    bal = FinancialManager.get_student_balance(student_id, config.Config.CURRENT_ACADEMIC_YEAR, fee_type_id=fee_type_id)
                    filtered_balance_var.set(f"Filtered Balance: {format_currency(bal.get('balance', 0))}")
                except Exception:
                    filtered_balance_var.set('')

                # Update summary
                summary_var.set(f"Total Payments: {format_currency(total)}")

            # Bind selection change
            fee_combo.bind('<<ComboboxSelected>>', lambda e: reload_payments())

            # initial load
            reload_payments()

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
        ttk.Combobox(dialog, textvariable=method_var, values=['Cash', 'Mobile money', 'Bank Transfer', 'Check', 'Other']).pack(pady=5)
        
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
            from pathlib import Path
            from reports.generators.financial_report import generate_financial_summary_report

            academic_year, term = self._current_finance_view()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_term = re.sub(r'[^A-Za-z0-9_-]+', '_', term).strip('_') or 'term'
            reports_dir = Path(config.Config.PATHS.get('reports', config.Config.USER_DATA_DIR))
            reports_dir.mkdir(parents=True, exist_ok=True)
            filename = reports_dir / f"financial_summary_{academic_year}_{safe_term}_{timestamp}.pdf"
            generate_financial_summary_report(str(filename), academic_year=academic_year, term=term)
            messagebox.showinfo("Success", f"Financial report generated:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
    
    def export_financial_data(self):
        """Export financial data to Excel"""
        try:
            import csv
            from pathlib import Path
            from models.finance import FinancialManager

            academic_year, term = self._current_finance_view()
            summary = FinancialManager.get_term_financial_summary(academic_year, term)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_term = re.sub(r'[^A-Za-z0-9_-]+', '_', term).strip('_') or 'term'
            exports_dir = Path(config.Config.PATHS.get('exports', config.Config.USER_DATA_DIR))
            exports_dir.mkdir(parents=True, exist_ok=True)
            filename = exports_dir / f"financial_summary_{academic_year}_{safe_term}_{timestamp}.csv"

            with open(filename, 'w', newline='', encoding='utf-8') as handle:
                writer = csv.writer(handle)
                writer.writerow(['Academic Year', academic_year])
                writer.writerow(['Term', term])
                writer.writerow(['Selected Term Income', summary.get('total_income', 0)])
                writer.writerow(['Selected Term Expenses', summary.get('total_expenses', 0)])
                writer.writerow(['Selected Term Net', summary.get('net_balance', 0)])
                writer.writerow(['Academic Year Income', summary.get('academic_year_total_income', 0)])
                writer.writerow(['Academic Year Expenses', summary.get('academic_year_total_expenses', 0)])
                writer.writerow(['Academic Year Net', summary.get('academic_year_net_balance', 0)])
                writer.writerow(['Outstanding Fees', summary.get('outstanding_fees', 0)])
                writer.writerow([])
                writer.writerow(['Monthly Breakdown'])
                writer.writerow(['Month', 'Income', 'Expenses', 'Net', 'Payments'])
                for row in summary.get('monthly_breakdown') or []:
                    writer.writerow([
                        row.get('month'),
                        row.get('income', 0),
                        row.get('expenses', 0),
                        row.get('net', 0),
                        row.get('payment_count', 0)
                    ])
                writer.writerow([])
                writer.writerow(['Fees Collected by Type'])
                writer.writerow(['Fee Type', 'Configured Terms', 'Selected Term', 'Academic Year', 'Payments'])
                for row in summary.get('fee_totals') or []:
                    writer.writerow([
                        row.get('fee_name'),
                        row.get('fee_terms', ''),
                        row.get('term_collected', 0),
                        row.get('academic_year_collected', 0),
                        row.get('term_payment_count', 0)
                    ])
                writer.writerow([])
                writer.writerow(['Expense Categories'])
                writer.writerow(['Category', 'Count', 'Total'])
                for row in summary.get('expense_categories') or []:
                    writer.writerow([
                        row.get('category'),
                        row.get('expense_count', 0),
                        row.get('total_amount', 0)
                    ])

            messagebox.showinfo("Export", f"Term financial data exported:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {str(e)}")
    
    def print_financial_summary(self):
        """Print financial summary"""
        try:
            messagebox.showinfo("Print", "Financial summary would be sent to printer")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print: {str(e)}")

    # Staff Salaries Methods
    def _get_salary_month_options(self, months_back=24):
        """Return list of YYYY-MM options from current month backwards."""
        out = []
        cur = date.today().replace(day=1)
        for _ in range(months_back):
            out.append(cur.strftime('%Y-%m'))
            if cur.month == 1:
                cur = cur.replace(year=cur.year - 1, month=12)
            else:
                cur = cur.replace(month=cur.month - 1)
        return out

    def _selected_salary_month(self):
        """Get selected salary month in YYYY-MM."""
        val = (self.salary_month_var.get() or '').strip()
        if re.match(r'^\d{4}-\d{2}$', val):
            return val
        return date.today().strftime('%Y-%m')

    def _salary_month_bounds(self):
        """Get [start, next_month_start) dates for selected salary month."""
        ym = self._selected_salary_month()
        start = datetime.strptime(f"{ym}-01", "%Y-%m-%d").date()
        if start.month == 12:
            end_excl = date(start.year + 1, 1, 1)
        else:
            end_excl = date(start.year, start.month + 1, 1)
        return start, end_excl

    def load_staff_salaries(self):
        """Load staff salaries and their advances"""
        try:
            selected_month = self._selected_salary_month()
            use_snapshot = True
            try:
                from models.finance import FinancialManager
                FinancialManager.generate_monthly_salary_snapshot(selected_month)
            except Exception as e:
                # Keep staff salaries usable even if monthly snapshot table/migration fails.
                use_snapshot = False
                print(f"Salary snapshot fallback enabled: {e}")

            # Load teachers dropdown
            query = "SELECT teacher_id, teacher_code, first_name, last_name, salary_amount, allowance_amount FROM teachers WHERE is_active = 1 ORDER BY last_name, first_name"
            teachers = db.execute_query(query, params=(), fetch=True)
            teacher_list = [f"{t['teacher_id']}: {t['first_name']} {t['last_name']} ({t['teacher_code']})" for t in teachers]
            self.staff_teacher_combo['values'] = teacher_list
            
            # If no teacher selected, select the first one
            if teacher_list and not self.staff_teacher_var.get():
                self.staff_teacher_combo.current(0)
                self.on_staff_teacher_selected()
            elif self.staff_teacher_var.get():
                self.on_staff_teacher_selected()
            else:
                self.clear_staff_info()
                self.load_advances_list(None)

            # Update salary totals for all active staff
            try:
                if use_snapshot:
                    total_query = """
                        SELECT
                            COALESCE(SUM(base_salary), 0) as total_salary_only,
                            COALESCE(SUM(gross_salary), 0) as total_salary_with_allowances,
                            COALESCE(SUM(net_salary), 0) as total_net_salary
                        FROM teacher_salary_monthly
                        WHERE payroll_month = %s
                    """
                    totals = db.execute_query(total_query, (selected_month,), fetch=True) or []
                else:
                    start_date, end_exclusive = self._salary_month_bounds()
                    total_query = """
                        SELECT
                            COALESCE(SUM(COALESCE(t.salary_amount, 0)), 0) as total_salary_only,
                            COALESCE(SUM(COALESCE(t.salary_amount, 0) + COALESCE(t.allowance_amount, 0)), 0) as total_salary_with_allowances,
                            COALESCE(SUM(COALESCE(t.salary_amount, 0) + COALESCE(t.allowance_amount, 0) - COALESCE(a.total_advances, 0)), 0) as total_net_salary
                        FROM teachers t
                        LEFT JOIN (
                            SELECT teacher_id, COALESCE(SUM(advance_amount), 0) AS total_advances
                            FROM teacher_salary_advances
                            WHERE status IN ('Approved', 'Deducted')
                              AND advance_date >= %s
                              AND advance_date < %s
                            GROUP BY teacher_id
                        ) a ON a.teacher_id = t.teacher_id
                        WHERE t.is_active = 1
                    """
                    totals = db.execute_query(total_query, (start_date, end_exclusive), fetch=True) or []
                row = totals[0] if totals else {}
                self.total_salary_only_var.set(format_currency(float(row.get('total_salary_only') or 0)))
                self.total_salary_with_allowances_var.set(format_currency(float(row.get('total_salary_with_allowances') or 0)))
                self.total_salary_net_var.set(format_currency(float(row.get('total_net_salary') or 0)))
            except Exception:
                self.total_salary_only_var.set("---")
                self.total_salary_with_allowances_var.set("---")
                self.total_salary_net_var.set("---")
                
        except Exception as e:
            print(f"Error loading staff salaries: {e}")
    
    def on_staff_teacher_selected(self, event=None):
        """Handle teacher selection change"""
        try:
            sel = self.staff_teacher_var.get()
            if not sel:
                self.clear_staff_info()
                self.load_advances_list(None)
                return
            
            teacher_id = int(sel.split(':')[0])
            selected_month = self._selected_salary_month()
            
            # Load teacher info
            result = []
            try:
                query = """
                    SELECT
                        t.teacher_code,
                        t.first_name,
                        t.last_name,
                        COALESCE(tsm.base_salary, t.salary_amount, 0) AS salary_amount,
                        COALESCE(tsm.allowance_amount, t.allowance_amount, 0) AS allowance_amount,
                        COALESCE(tsm.advances_amount, 0) AS total_advances,
                        COALESCE(tsm.net_salary, (COALESCE(t.salary_amount, 0) + COALESCE(t.allowance_amount, 0))) AS net_salary,
                        COALESCE(tsm.is_paid, 0) AS is_paid
                    FROM teachers t
                    LEFT JOIN teacher_salary_monthly tsm
                      ON tsm.teacher_id = t.teacher_id
                     AND tsm.payroll_month = %s
                    WHERE t.teacher_id = %s
                """
                result = db.execute_query(query, (selected_month, teacher_id), fetch=True) or []
            except Exception:
                # Fallback when monthly snapshot table is unavailable.
                start_date, end_exclusive = self._salary_month_bounds()
                query = """
                    SELECT teacher_code, first_name, last_name, salary_amount, allowance_amount
                    FROM teachers
                    WHERE teacher_id = %s
                """
                base_res = db.execute_query(query, (teacher_id,), fetch=True) or []
                if base_res:
                    t = base_res[0]
                    adv_q = """
                        SELECT COALESCE(SUM(advance_amount), 0) AS total
                        FROM teacher_salary_advances
                        WHERE teacher_id = %s
                          AND status IN ('Approved', 'Deducted')
                          AND advance_date >= %s
                          AND advance_date < %s
                    """
                    adv_res = db.execute_query(adv_q, (teacher_id, start_date, end_exclusive), fetch=True) or []
                    total_advances = float(adv_res[0].get('total') or 0) if adv_res else 0.0
                    salary = float(t.get('salary_amount') or 0)
                    allowance = float(t.get('allowance_amount') or 0)
                    t['total_advances'] = total_advances
                    t['net_salary'] = (salary + allowance) - total_advances
                    t['is_paid'] = 0
                    result = [t]
            
            if result:
                teacher = result[0]
                code = teacher.get('teacher_code', '')
                name = f"{teacher.get('first_name', '')} {teacher.get('last_name', '')}"
                salary = float(teacher.get('salary_amount', 0) or 0)
                allowance = float(teacher.get('allowance_amount', 0) or 0)
                total_advances = float(teacher.get('total_advances', 0) or 0)
                net_salary = float(teacher.get('net_salary', 0) or 0)
                
                # Update info labels
                self.staff_code_var.set(code)
                self.staff_name_var.set(name)
                self.staff_salary_var.set(format_currency(salary))
                self.staff_allowance_var.set(format_currency(allowance))
                self.staff_advances_var.set(format_currency(total_advances))
                self.staff_net_var.set(format_currency(net_salary))
                self.staff_salary_status_var.set("Active")
                self.salary_paid_var.set(bool(int(teacher.get('is_paid') or 0)))

                # Preload allowance form
                try:
                    self.allowance_amount_var.set(str(allowance))
                except Exception:
                    pass
                
                # Load advances list
                self.load_advances_list(teacher_id)
            else:
                self.clear_staff_info()
                self.load_advances_list(None)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load teacher info: {e}")
            print(f"Error on_staff_teacher_selected: {e}")
    
    def clear_staff_info(self):
        """Clear staff info display"""
        self.staff_code_var.set("---")
        self.staff_name_var.set("---")
        self.staff_salary_var.set("---")
        self.staff_allowance_var.set("---")
        self.staff_advances_var.set("---")
        self.staff_net_var.set("---")
        self.staff_salary_status_var.set("---")
        self.salary_paid_var.set(False)
        try:
            self.allowance_amount_var.set("")
        except Exception:
            pass

    def update_salary_paid_status(self):
        """Set salary paid/unpaid for selected teacher in selected month."""
        try:
            sel = self.staff_teacher_var.get()
            if not sel:
                messagebox.showwarning("No Selection", "Please select a teacher")
                return
            teacher_id = int(sel.split(':')[0])
            payroll_month = self._selected_salary_month()
            is_paid = 1 if self.salary_paid_var.get() else 0

            # Ensure monthly snapshot row exists before updating paid flag.
            try:
                from models.finance import FinancialManager
                FinancialManager.generate_monthly_salary_snapshot(payroll_month)
            except Exception:
                pass

            db.execute_query(
                """
                INSERT INTO teacher_salary_monthly (teacher_id, payroll_month, is_paid)
                VALUES (%s, %s, %s)
                """ + db.upsert_clause(("teacher_id", "payroll_month"), set_new=("is_paid",)),
                (teacher_id, payroll_month, is_paid)
            )
            messagebox.showinfo("Success", "Salary paid status updated")
            self.on_staff_teacher_selected()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update paid status: {e}")

    def save_allowance(self):
        """Save allowance amount for selected teacher"""
        try:
            sel = self.staff_teacher_var.get()
            if not sel:
                messagebox.showwarning("No Selection", "Please select a teacher")
                return
            try:
                teacher_id = int(sel.split(':')[0])
            except Exception:
                messagebox.showwarning("Invalid Selection", "Please select a valid teacher")
                return
            try:
                allowance = float(self.allowance_amount_var.get().strip() or 0.0)
            except Exception:
                messagebox.showwarning("Invalid Amount", "Please enter a valid allowance amount")
                return
            db.execute_query(
                "UPDATE teachers SET allowance_amount = %s WHERE teacher_id = %s",
                (allowance, teacher_id)
            )
            messagebox.showinfo("Success", "Allowance updated successfully")
            self.on_staff_teacher_selected()
            self.load_staff_salaries()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update allowance: {str(e)}")

    def clear_allowance_form(self):
        """Clear allowance form"""
        try:
            self.allowance_amount_var.set("")
        except Exception:
            pass
    
    def load_advances_list(self, teacher_id):
        """Load advances list for selected teacher"""
        # Clear existing items
        for item in self.advances_tree.get_children():
            self.advances_tree.delete(item)
        
        try:
            if teacher_id is None:
                return
            
            status_filter = self.staff_status_var.get()
            start_date, end_exclusive = self._salary_month_bounds()
            base_query = """
                SELECT tsa.advance_id, t.first_name, t.last_name, tsa.advance_amount, tsa.advance_date, tsa.description, tsa.status
                FROM teacher_salary_advances tsa
                JOIN teachers t ON tsa.teacher_id = t.teacher_id
                WHERE tsa.teacher_id = %s
                  AND tsa.advance_date >= %s
                  AND tsa.advance_date < %s
            """
            
            params = (teacher_id, start_date, end_exclusive)
            if status_filter != "All":
                base_query += " AND tsa.status = %s"
                params = (teacher_id, start_date, end_exclusive, status_filter)
            
            results = db.execute_query(base_query, params, fetch=True)
            
            if results:
                for row in results:
                    self.advances_tree.insert('', 'end', values=(
                        row['advance_id'],
                        f"{row['first_name']} {row['last_name']}",
                        format_currency(float(row['advance_amount'])),
                        row['advance_date'],
                        row.get('description', ''),
                        row['status']
                    ))
        except Exception as e:
            print(f"Error loading advances list: {e}")
    
    def record_salary_advance(self):
        """Record a new salary advance"""
        try:
            sel = self.staff_teacher_var.get()
            if not sel:
                messagebox.showwarning("Select", "Please select a teacher")
                return
            
            teacher_id = int(sel.split(':')[0])
            amount_str = self.advance_amount_var.get().strip()
            if not amount_str:
                messagebox.showwarning("Input", "Please enter advance amount")
                return
            
            try:
                amount = float(amount_str)
            except ValueError:
                messagebox.showwarning("Input", "Please enter a valid amount")
                return
            
            if amount <= 0:
                messagebox.showwarning("Input", "Amount must be greater than zero")
                return
            
            description = self.advance_desc_var.get().strip()
            advance_date = self.advance_date_var.get().strip()
            status = self.advance_status_var.get()
            
            # Insert advance record
            query = """
                INSERT INTO teacher_salary_advances (teacher_id, advance_amount, advance_date, description, status)
                VALUES (%s, %s, %s, %s, %s)
            """
            db.execute_query(query, (teacher_id, amount, advance_date, description, status))
            
            messagebox.showinfo("Success", "Salary advance recorded successfully")
            self.clear_advance_form()
            self.load_staff_salaries()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record advance: {e}")
    
    def edit_salary_advance(self):
        """Edit selected salary advance"""
        try:
            selected = self.advances_tree.selection()
            if not selected:
                messagebox.showwarning("Select", "Select an advance to edit")
                return
            
            item = self.advances_tree.item(selected[0], 'values')
            advance_id = int(item[0])
            
            # Fetch advance details
            query = "SELECT * FROM teacher_salary_advances WHERE advance_id = %s"
            result = db.execute_query(query, (advance_id,), fetch=True)
            
            if not result:
                messagebox.showerror("Error", "Advance record not found")
                return
            
            advance = result[0]
            
            # Create edit dialog
            dialog = tk.Toplevel(self.frame)
            dialog.title("Edit Salary Advance")
            dialog.geometry("400x300")
            
            # Form fields
            ttk.Label(dialog, text="Amount:").grid(row=0, column=0, sticky='w', padx=10, pady=5)
            amount_var = tk.StringVar(value=str(advance['advance_amount']))
            ttk.Entry(dialog, textvariable=amount_var, width=30).grid(row=0, column=1, padx=10, pady=5)
            
            ttk.Label(dialog, text="Description:").grid(row=1, column=0, sticky='w', padx=10, pady=5)
            desc_var = tk.StringVar(value=advance.get('description', ''))
            ttk.Entry(dialog, textvariable=desc_var, width=30).grid(row=1, column=1, padx=10, pady=5)
            
            ttk.Label(dialog, text="Date:").grid(row=2, column=0, sticky='w', padx=10, pady=5)
            date_var = tk.StringVar(value=advance['advance_date'])
            ttk.Entry(dialog, textvariable=date_var, width=30).grid(row=2, column=1, padx=10, pady=5)
            
            ttk.Label(dialog, text="Status:").grid(row=3, column=0, sticky='w', padx=10, pady=5)
            status_var = tk.StringVar(value=advance['status'])
            status_combo = ttk.Combobox(dialog, textvariable=status_var, values=['Pending', 'Approved', 'Deducted'], state='readonly', width=28)
            status_combo.grid(row=3, column=1, padx=10, pady=5)
            
            def save_changes():
                try:
                    amount = float(amount_var.get())
                    if amount <= 0:
                        messagebox.showwarning("Input", "Amount must be greater than zero")
                        return
                    
                    query = "UPDATE teacher_salary_advances SET advance_amount=%s, description=%s, advance_date=%s, status=%s WHERE advance_id=%s"
                    db.execute_query(query, (amount, desc_var.get(), date_var.get(), status_var.get(), advance_id))
                    messagebox.showinfo("Success", "Advance updated successfully")
                    dialog.destroy()
                    self.load_staff_salaries()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update: {e}")
            
            btn_frame = ttk.Frame(dialog)
            btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
            ttk.Button(btn_frame, text="Save", command=save_changes).pack(side='left', padx=5)
            ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit advance: {e}")
    
    def delete_salary_advance(self):
        """Delete selected salary advance"""
        try:
            selected = self.advances_tree.selection()
            if not selected:
                messagebox.showwarning("Select", "Select an advance to delete")
                return
            
            item = self.advances_tree.item(selected[0], 'values')
            advance_id = int(item[0])
            
            if not messagebox.askyesno("Confirm", "Permanently delete this advance record?"):
                return
            
            query = "DELETE FROM teacher_salary_advances WHERE advance_id = %s"
            db.execute_query(query, (advance_id,))
            messagebox.showinfo("Success", "Advance deleted successfully")
            self.load_staff_salaries()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete advance: {e}")
    
    def clear_advance_form(self):
        """Clear the advance recording form"""
        self.advance_amount_var.set("")
        self.advance_desc_var.set("")
        self.advance_date_var.set(date.today().strftime('%Y-%m-%d'))
        self.advance_status_var.set("Pending")
