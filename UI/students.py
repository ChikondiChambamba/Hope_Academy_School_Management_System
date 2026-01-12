"""
Students Tab - UI for managing students
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import config
from models.student import Student, StudentManager
from models.finance import FinancialManager
from UI.dialogs import StudentDialog, FeePaymentDialog, ConfirmationDialog
from utils.helpers import format_currency, parse_currency

class StudentsTab:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        self.load_students()
    
    def setup_ui(self):
        """Setup students tab UI"""
        role = getattr(config.Config, 'CURRENT_USER_ROLE', 'Administrator')
        # Main container
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(
            main_container, 
            text="Student Management",
            style='Title.TLabel'
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Control buttons frame (top)
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill='x', pady=(0, 10))

        # Left side: class list + action buttons
        left_frame = ttk.Frame(controls_frame)
        left_frame.pack(side='left')

        # Class horizontal button bar for quick selection (Reception -> Grade 7)
        self.default_classes = ['Reception', 'Nursery', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6', 'Grade 7']
        class_frame = ttk.Frame(left_frame)
        class_frame.pack(side='left', padx=(0,10), fill='x')
        ttk.Label(class_frame, text='Classes:').pack(anchor='w')
        # Horizontal buttons
        self.class_buttons = {}
        btn_row = ttk.Frame(class_frame)
        btn_row.pack(fill='x')
        for cls in self.default_classes:
            b = tk.Button(btn_row, text=cls, padx=6, pady=2, relief='raised', command=lambda c=cls: self.on_class_button_select(c))
            b.pack(side='left', padx=3, pady=2)
            # store default colors so we can restore them when toggling
            try:
                b.default_bg = b.cget('bg')
            except Exception:
                b.default_bg = None
            try:
                b.default_fg = b.cget('fg')
            except Exception:
                b.default_fg = None
            self.class_buttons[cls] = b
        # Delete class button
        del_btn = ttk.Button(class_frame, text='Delete Class', command=self.delete_class, style='Danger.TButton')
        del_btn.pack(side='left', padx=6)
        
        self.add_button = ttk.Button(
            left_frame, 
            text="Add Student",
            command=self.add_student,
            style='Success.TButton'
        )
        self.add_button.pack(side='left', padx=(0, 5))
        
        self.edit_button = ttk.Button(
            left_frame, 
            text="Edit Student",
            command=self.edit_student,
            style='Primary.TButton'
        )
        self.edit_button.pack(side='left', padx=5)
        
        self.delete_button = ttk.Button(
            left_frame, 
            text="Delete Student",
            command=self.delete_student,
            style='Danger.TButton'
        )
        self.delete_button.pack(side='left', padx=5)
        
        self.fee_button = ttk.Button(
            left_frame,
            text="Record Fee Payment",
            command=self.record_fee_payment,
            style='Warning.TButton'
        )
        self.fee_button.pack(side='left', padx=5)

        # If role is Headteacher, disable fee actions
        if role == 'Headteacher':
            try:
                self.fee_button.state(['disabled'])
            except Exception:
                self.fee_button.config(state='disabled')

        # Initially disable action buttons until a class is selected
        for btn in (self.add_button, self.edit_button, self.delete_button):
            btn.state(['disabled'])
        # fee_button already handled above (may be disabled for Headteacher)
        
        # Right side search
        right_frame = ttk.Frame(controls_frame)
        right_frame.pack(side='right')
        
        # Filter by class (kept for search convenience)
        ttk.Label(right_frame, text="Class:").pack(side='left', padx=(0, 5))
        self.class_var = tk.StringVar()
        self.class_combo = ttk.Combobox(
            right_frame, 
            textvariable=self.class_var,
            values=self.get_class_list(),
            width=15,
            state='readonly'
        )
        self.class_combo.pack(side='left', padx=(0, 10))
        self.class_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_by_class())
        
        # Show inactive checkbox
        self.show_inactive_var = tk.BooleanVar(value=False)
        self.show_inactive_cb = ttk.Checkbutton(
            right_frame,
            text='Show Inactive',
            variable=self.show_inactive_var,
            command=self.on_show_inactive_toggle
        )
        self.show_inactive_cb.pack(side='left', padx=(0, 10))
        
        # Search
        ttk.Label(right_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(right_frame, textvariable=self.search_var, width=25)
        self.search_entry.pack(side='left', padx=(0, 5))
        
        search_button = ttk.Button(
            right_frame,
            text="Go",
            command=self.search_students,
            width=5
        )
        # Stack the Go and Refresh buttons vertically so they don't stretch sideways
        buttons_frame = ttk.Frame(right_frame, width=60)
        buttons_frame.pack(side='left', padx=(0, 5))
        # Prevent the frame from expanding to fill available horizontal space
        try:
            buttons_frame.pack_propagate(False)
        except Exception:
            pass

        search_button.pack(in_=buttons_frame, side='top', pady=(0, 4))

        refresh_button = ttk.Button(
            buttons_frame,
            text="Refresh",
            command=self.load_students,
            width=8
        )
        refresh_button.pack(side='top')
        
        # Bind Enter key to search
        self.search_entry.bind('<Return>', lambda e: self.search_students())
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill='both', expand=True)
        
        # Student List Tab
        self.students_frame = ttk.Frame(notebook)
        notebook.add(self.students_frame, text="Student List")
        self.setup_students_list()
        # Fee Balances Tab: hide for Headteacher role
        role = getattr(config.Config, 'CURRENT_USER_ROLE', 'Administrator')
        self.balances_frame = ttk.Frame(notebook)
        if role != 'Headteacher':
            notebook.add(self.balances_frame, text="Fee Balances")
            self.setup_fee_balances()
        else:
            # Keep a placeholder frame so refresh_data calls won't fail
            self.balances_frame = ttk.Frame(notebook)
        
        # Status label
        self.status_label = ttk.Label(main_container, text="")
        self.status_label.pack(anchor='w', pady=(10, 0))
    
    def setup_students_list(self):
        """Setup student list treeview"""
        tree_frame = ttk.Frame(self.students_frame)
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Define columns
        role = getattr(config.Config, 'CURRENT_USER_ROLE', 'Administrator')
        columns = ['ID', 'Code', 'First Name', 'Last Name', 'Class', 'Parent', 'Phone', 'Enrollment Date', 'Status']
        # Show financial Balance column to roles other than Headteacher
        if role != 'Headteacher':
            # insert Balance before Status
            columns.insert(-1, 'Balance')
        columns = tuple(columns)
        
        # Create treeview
        self.students_tree = ttk.Treeview(
            tree_frame, 
            columns=columns,
            show='headings',
            selectmode='browse',
            height=20
        )
        
        # Configure columns
        column_widths = {
            'ID': 50,
            'Code': 80,
            'First Name': 100,
            'Last Name': 100,
            'Class': 80,
            'Parent': 120,
            'Phone': 100,
            'Enrollment Date': 100,
            'Balance': 80,
            'Status': 80
        }
        
        for col in columns:
            self.students_tree.heading(col, text=col)
            self.students_tree.column(col, width=column_widths.get(col, 100))
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.students_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.students_tree.xview)
        self.students_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.students_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Bind double-click to preview student details
        self.students_tree.bind('<Double-1>', lambda e: self.preview_student())
        
        # Bind selection change
        self.students_tree.bind('<<TreeviewSelect>>', self.on_selection_change)
    
    def setup_fee_balances(self):
        """Setup fee balances treeview"""
        tree_frame = ttk.Frame(self.balances_frame)
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Define columns
        columns = ('ID', 'Code', 'Name', 'Class', 'Total Due', 'Paid', 'Balance')
        
        # Create treeview
        self.balances_tree = ttk.Treeview(
            tree_frame, 
            columns=columns,
            show='headings',
            selectmode='browse',
            height=20
        )
        
        # Configure columns
        column_widths = {
            'ID': 50,
            'Code': 80,
            'Name': 150,
            'Class': 80,
            'Total Due': 100,
            'Paid': 100,
            'Balance': 100
        }
        
        for col in columns:
            self.balances_tree.heading(col, text=col)
            self.balances_tree.column(col, width=column_widths.get(col, 100))
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.balances_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.balances_tree.xview)
        self.balances_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.balances_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Sort by balance (descending)
        self.balances_tree.heading('Balance', command=lambda: self.sort_balances())
    
    def get_class_list(self):
        """Get list of unique classes"""
        try:
            # Query database for distinct classes
            from database.connection import db
            if getattr(self, 'show_inactive_var', None) and self.show_inactive_var.get():
                query = "SELECT DISTINCT class FROM students ORDER BY class"
                results = db.execute_query(query, fetch=True)
            else:
                query = "SELECT DISTINCT class FROM students WHERE is_active = 1 ORDER BY class"
                results = db.execute_query(query, fetch=True)
            
            classes = [r['class'] for r in results] if results else []
            return ['All'] + classes
        except:
            return ['All']

    def on_class_listbox_select(self, event):
        """Deprecated: kept for compatibility. Use `on_class_button_select` instead."""
        return

    def on_class_button_select(self, class_name):
        """Handle selection from the horizontal class buttons"""
        # Visual toggle
        primary = getattr(config.Config, 'UI', {}).get('primary_color', '#2E86C1')
        sel_fg = 'white'

        for name, btn in self.class_buttons.items():
            try:
                # reset appearance
                btn.config(relief='raised')
                if getattr(btn, 'default_bg', None) is not None:
                    btn.config(bg=btn.default_bg)
                if getattr(btn, 'default_fg', None) is not None:
                    btn.config(fg=btn.default_fg)
            except Exception:
                pass

        # Mark selected
        sel_btn = self.class_buttons.get(class_name)
        if sel_btn:
            try:
                sel_btn.config(relief='sunken')
                # Apply themed color
                sel_btn.config(bg=primary, fg=sel_fg, activebackground=primary)
            except Exception:
                pass

        # Set the combobox and filter
        self.class_var.set(class_name)
        try:
            self.class_combo.set(class_name)
        except Exception:
            pass

        # Enable action buttons
        for btn in (self.add_button, self.edit_button, self.delete_button, self.fee_button):
            btn.state(['!disabled'])

        # Apply filter
        self.filter_by_class()
    
    def load_students(self):
        """Load students into treeview"""
        # Clear existing items
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        
        try:
            # Determine whether to include inactive students
            include_inactive = self.show_inactive_var.get() if getattr(self, 'show_inactive_var', None) else False
            students = Student.get_all(active_only=(not include_inactive))
            
            # Insert into treeview
            for student in students:
                status = "Active" if student.is_active else "Inactive"
                balance = student.balance
                
                # Color coding for balance
                from utils.helpers import format_currency
                if balance > 0:
                    balance_display = f"{format_currency(balance)} ✗"
                else:
                    balance_display = f"{format_currency(abs(balance))} ✓"
                # Build values respecting whether Balance column is present
                role = getattr(config.Config, 'CURRENT_USER_ROLE', 'Administrator')
                if role != 'Headteacher':
                    values = (
                        student.student_id,
                        student.student_code,
                        student.first_name,
                        student.last_name,
                        student.class_name,
                        student.parent_name or '',
                        student.parent_phone or '',
                        student.enrollment_date.strftime('%Y-%m-%d') if student.enrollment_date else '',
                        balance_display,
                        status
                    )
                else:
                    # Headteacher: omit balance
                    values = (
                        student.student_id,
                        student.student_code,
                        student.first_name,
                        student.last_name,
                        student.class_name,
                        student.parent_name or '',
                        student.parent_phone or '',
                        student.enrollment_date.strftime('%Y-%m-%d') if student.enrollment_date else '',
                        status
                    )

                self.students_tree.insert('', 'end', values=values)
            
            # Update status
            count = len(students)
            self.status_label.config(text=f"Total Students: {count}")
            
            # Load fee balances if the balances tree was created (not shown for Headteacher)
            if hasattr(self, 'balances_tree'):
                try:
                    self.load_fee_balances()
                except Exception:
                    pass
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load students: {str(e)}")
            self.status_label.config(text="Error loading students")
    
    def load_fee_balances(self):
        """Load fee balances into balances treeview"""
        # Clear existing items
        for item in self.balances_tree.get_children():
            self.balances_tree.delete(item)
        
        try:
            # Get student balances
            balances = FinancialManager.get_student_balances()
            
            # Insert into treeview
            for bal in balances:
                student_id = bal['student_id']
                student_code = bal['student_code']
                student_name = bal['student_name']
                class_name = bal['class']
                total_due = float(bal['total_due'])
                total_paid = float(bal['total_paid'])
                balance = float(bal['balance'])
                
                # Color tag based on balance
                tags = ('overdue',) if balance > 0 else ('paid',) if balance < 0 else ('partial',)
                
                self.balances_tree.insert('', 'end', values=(
                    student_id,
                    student_code,
                    student_name,
                    class_name,
                    format_currency(total_due),
                    format_currency(total_paid),
                    format_currency(balance)
                ), tags=tags)
            
            # Configure tag colors
            self.balances_tree.tag_configure('overdue', foreground='red')
            self.balances_tree.tag_configure('paid', foreground='green')
            self.balances_tree.tag_configure('partial', foreground='orange')
            
        except Exception as e:
            print(f"Error loading fee balances: {e}")
    
    def sort_balances(self):
        """Sort balances by balance amount"""
        items = [(self.balances_tree.set(item, 'Balance'), item) 
            for item in self.balances_tree.get_children('')]

        # Sort by balance value (use parse_currency to extract number)
        items.sort(key=lambda x: float(parse_currency(x[0])))
        
        for index, (val, item) in enumerate(items):
            self.balances_tree.move(item, '', index)
    
    def search_students(self):
        """Search students by name or code"""
        search_term = self.search_var.get().strip()
        
        if not search_term:
            self.load_students()
            return
        
        # Clear existing items
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        
        try:
            include_inactive = self.show_inactive_var.get() if getattr(self, 'show_inactive_var', None) else False
            # Search students
            students = Student.search(search_term, active_only=(not include_inactive))
            
            # Insert results
            for student in students:
                status = "Active" if student.is_active else "Inactive"
                balance = student.balance
                balance_display = f"{format_currency(balance)} ✗" if balance > 0 else f"{format_currency(abs(balance))} ✓"
                role = getattr(config.Config, 'CURRENT_USER_ROLE', 'Administrator')
                if role != 'Headteacher':
                    values = (
                        student.student_id,
                        student.student_code,
                        student.first_name,
                        student.last_name,
                        student.class_name,
                        student.parent_name or '',
                        student.parent_phone or '',
                        student.enrollment_date.strftime('%Y-%m-%d') if student.enrollment_date else '',
                        balance_display,
                        status
                    )
                else:
                    values = (
                        student.student_id,
                        student.student_code,
                        student.first_name,
                        student.last_name,
                        student.class_name,
                        student.parent_name or '',
                        student.parent_phone or '',
                        student.enrollment_date.strftime('%Y-%m-%d') if student.enrollment_date else '',
                        status
                    )

                self.students_tree.insert('', 'end', values=values)
            
            # Update status
            count = len(students)
            self.status_label.config(text=f"Found {count} student(s) matching '{search_term}'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {str(e)}")
    
    def filter_by_class(self):
        """Filter students by selected class"""
        selected_class = self.class_var.get()
        
        if not selected_class or selected_class == 'All':
            self.load_students()
            return
        
        # Clear existing items
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        
        try:
            include_inactive = self.show_inactive_var.get() if getattr(self, 'show_inactive_var', None) else False
            # Get students by class
            students = Student.get_by_class(selected_class, active_only=(not include_inactive))
            
            # Insert into treeview
            for student in students:
                status = "Active" if student.is_active else "Inactive"
                balance = student.balance
                balance_display = f"{format_currency(balance)} ✗" if balance > 0 else f"{format_currency(abs(balance))} ✓"
                role = getattr(config.Config, 'CURRENT_USER_ROLE', 'Administrator')
                if role != 'Headteacher':
                    values = (
                        student.student_id,
                        student.student_code,
                        student.first_name,
                        student.last_name,
                        student.class_name,
                        student.parent_name or '',
                        student.parent_phone or '',
                        student.enrollment_date.strftime('%Y-%m-%d') if student.enrollment_date else '',
                        balance_display,
                        status
                    )
                else:
                    values = (
                        student.student_id,
                        student.student_code,
                        student.first_name,
                        student.last_name,
                        student.class_name,
                        student.parent_name or '',
                        student.parent_phone or '',
                        student.enrollment_date.strftime('%Y-%m-%d') if student.enrollment_date else '',
                        status
                    )

                self.students_tree.insert('', 'end', values=values)
            
            # Update status
            count = len(students)
            self.status_label.config(text=f"Class {selected_class}: {count} student(s)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to filter by class: {str(e)}")

    def on_show_inactive_toggle(self):
        """Handler for Show Inactive checkbox - refresh class list and current view."""
        try:
            # Refresh class combobox values
            vals = self.get_class_list()
            self.class_combo['values'] = vals
            # If current selection is not in list, reset to 'All'
            current = self.class_var.get()
            if current not in vals:
                self.class_var.set('All')
                try:
                    self.class_combo.set('All')
                except Exception:
                    pass

            # Reload students respecting the new flag
            self.load_students()
        except Exception:
            pass
    
    def add_student(self):
        """Open dialog to add new student"""
        # If a class is selected in the left listbox, prefill it in the dialog
        selected_class = None
        # Check selected class from class_var (set when a class button is pressed)
        if self.class_var.get() and self.class_var.get() != 'All':
            selected_class = self.class_var.get()

        student_obj = None
        if selected_class:
            # create a lightweight Student object with default class
            from models.student import Student as StudentModel
            student_obj = StudentModel(class_name=selected_class)

        dialog = StudentDialog(self.frame, title="Add New Student", student=student_obj)
        dialog.show()
        
        # Refresh if student was added
        if dialog.result:
            self.load_students()
            # Update class filter combo
            self.class_combo['values'] = self.get_class_list()
    
    def edit_student(self):
        """Edit selected student"""
        selected = self.students_tree.selection()
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select a student to edit")
            return
        
        item = selected[0]
        values = self.students_tree.item(item, 'values')
        student_id = values[0]
        
        try:
            student = Student.get_by_id(student_id)
            if not student:
                messagebox.showerror("Error", "Student not found")
                return
            
            dialog = StudentDialog(self.frame, title="Edit Student", student=student)
            dialog.show()
            
            # Refresh if student was updated
            if dialog.result:
                self.load_students()
                # Update class filter combo
                self.class_combo['values'] = self.get_class_list()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit student: {str(e)}")
    
    def delete_student(self):
        """Delete (deactivate) selected student"""
        selected = self.students_tree.selection()
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select a student to delete")
            return
        
        item = selected[0]
        values = self.students_tree.item(item, 'values')
        student_id = values[0]
        student_name = f"{values[2]} {values[3]}"
        
        # Confirm deletion
        dialog = ConfirmationDialog(
            self.frame,
            title="Confirm Delete",
            message=f"Are you sure you want to delete student:\n{student_name}?",
            warning="This action cannot be undone. All attendance and fee records will be preserved."
        )
        
        if not dialog.show():
            return
        
        try:
            # Deactivate student
            success, message = StudentManager.delete_student(student_id)
            
            if success:
                messagebox.showinfo("Success", message)
                self.load_students()
                # Update class filter combo
                self.class_combo['values'] = self.get_class_list()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete student: {str(e)}")
    
    def record_fee_payment(self):
        """Record fee payment for selected student"""
        selected = self.students_tree.selection()
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select a student to record payment")
            return
        
        item = selected[0]
        values = self.students_tree.item(item, 'values')
        student_id = values[0]
        student_name = f"{values[2]} {values[3]}"
        
        try:
            # Get student details
            student = Student.get_by_id(student_id)
            if not student:
                messagebox.showerror("Error", "Student not found")
                return
            
            # Get fee summary
            fee_summary = StudentManager.get_student_financial_summary(student_id)
            
            # Show fee payment dialog
            dialog = FeePaymentDialog(
                self.frame, 
                title=f"Fee Payment - {student_name}",
                student=student,
                fee_summary=fee_summary
            )
            dialog.show()
            
            # Refresh if payment was recorded
            if dialog.result:
                self.load_students()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record payment: {str(e)}")

    def preview_student(self):
        """Preview selected student's full information (read-only)."""
        selected = self.students_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a student to preview")
            return

        item = selected[0]
        values = self.students_tree.item(item, 'values')
        student_id = values[0]

        try:
            student = Student.get_by_id(student_id)
            if not student:
                messagebox.showerror("Error", "Student not found")
                return

            from UI.dialogs import StudentPreviewDialog
            dialog = StudentPreviewDialog(self.frame, title=f"Student Preview - {student.first_name} {student.last_name}", student=student)
            dialog.show()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load student preview: {str(e)}")

    def delete_class(self):
        """Delete a class record; optionally delete or unassign students in it."""
        selected_class = self.class_var.get()
        if not selected_class or selected_class == 'All':
            messagebox.showwarning("No Class Selected", "Please select a class to delete")
            return

        # Confirm class deletion
        if not messagebox.askyesno("Delete Class", f"Are you sure you want to delete class '{selected_class}'?"):
            return

        # Ask whether to delete students in the class
        delete_students = messagebox.askyesno("Delete Students?", "Also delete all students in this class and their records?\nYes: delete students and their records.\nNo: unassign students from the class.")

        from database.connection import db
        try:
            # If deleting students, fetch them and remove
            if delete_students:
                students = Student.get_by_class(selected_class)
                for s in students:
                    StudentManager.delete_student(s.student_id)
            else:
                # Unassign students: set class to empty string
                query = "UPDATE students SET class = '' WHERE class = %s"
                db.execute_query(query, (selected_class,))

            # Delete class record from classes table if exists
            try:
                query = "DELETE FROM classes WHERE class_name = %s"
                db.execute_query(query, (selected_class,))
            except Exception:
                # If classes table doesn't exist or delete fails, ignore
                pass

            messagebox.showinfo("Success", f"Class '{selected_class}' removed.")
            # Refresh UI
            # Reset class_var and combobox
            self.class_var.set('All')
            try:
                self.class_combo['values'] = self.get_class_list()
                self.class_combo.set('All')
            except Exception:
                pass
            # Reset class buttons appearance
            for name, btn in self.class_buttons.items():
                try:
                    btn.config(relief='raised')
                    if getattr(btn, 'default_bg', None) is not None:
                        btn.config(bg=btn.default_bg)
                    if getattr(btn, 'default_fg', None) is not None:
                        btn.config(fg=btn.default_fg)
                except Exception:
                    pass

            self.load_students()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete class: {str(e)}")
    
    def on_selection_change(self, event):
        """Handle treeview selection change"""
        selected = self.students_tree.selection()
        self.edit_button.state(['!disabled'] if selected else ['disabled'])
        self.delete_button.state(['!disabled'] if selected else ['disabled'])
        self.fee_button.state(['!disabled'] if selected else ['disabled'])
    
    def refresh_data(self):
        """Public method to refresh data (called from main window)"""
        self.load_students()
        self.class_combo['values'] = self.get_class_list()