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

class StudentsTab:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        self.load_students()
    
    def setup_ui(self):
        """Setup students tab UI"""
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
        
        # Left side buttons
        left_frame = ttk.Frame(controls_frame)
        left_frame.pack(side='left')
        
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
        
        # Right side search
        right_frame = ttk.Frame(controls_frame)
        right_frame.pack(side='right')
        
        # Filter by class
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
        search_button.pack(side='left', padx=(0, 5))
        
        refresh_button = ttk.Button(
            right_frame,
            text="Refresh",
            command=self.load_students
        )
        refresh_button.pack(side='left')
        
        # Bind Enter key to search
        self.search_entry.bind('<Return>', lambda e: self.search_students())
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill='both', expand=True)
        
        # Student List Tab
        self.students_frame = ttk.Frame(notebook)
        notebook.add(self.students_frame, text="Student List")
        self.setup_students_list()
        
        # Fee Balances Tab
        self.balances_frame = ttk.Frame(notebook)
        notebook.add(self.balances_frame, text="Fee Balances")
        self.setup_fee_balances()
        
        # Status label
        self.status_label = ttk.Label(main_container, text="")
        self.status_label.pack(anchor='w', pady=(10, 0))
    
    def setup_students_list(self):
        """Setup student list treeview"""
        tree_frame = ttk.Frame(self.students_frame)
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Define columns
        columns = ('ID', 'Code', 'First Name', 'Last Name', 'Class', 
                  'Parent', 'Phone', 'Enrollment Date', 'Balance', 'Status')
        
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
        
        # Bind double-click to edit
        self.students_tree.bind('<Double-1>', lambda e: self.edit_student())
        
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
            query = "SELECT DISTINCT class FROM students WHERE is_active = 1 ORDER BY class"
            results = db.execute_query(query, fetch=True)
            
            classes = [r['class'] for r in results] if results else []
            return ['All'] + classes
        except:
            return ['All']
    
    def load_students(self):
        """Load students into treeview"""
        # Clear existing items
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        
        try:
            # Get all active students
            students = Student.get_all()
            
            # Insert into treeview
            for student in students:
                status = "Active" if student.is_active else "Inactive"
                balance = student.balance
                
                # Color coding for balance
                if balance > 0:
                    balance_display = f"${balance:,.2f} ✗"
                else:
                    balance_display = f"${abs(balance):,.2f} ✓"
                
                self.students_tree.insert('', 'end', values=(
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
                ))
            
            # Update status
            count = len(students)
            self.status_label.config(text=f"Total Students: {count}")
            
            # Load fee balances
            self.load_fee_balances()
            
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
                    f"${total_due:,.2f}",
                    f"${total_paid:,.2f}",
                    f"${balance:,.2f}"
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
        
        # Sort by balance value (extract number from string)
        items.sort(key=lambda x: float(x[0].replace('$', '').replace(',', '')))
        
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
            # Search students
            students = Student.search(search_term)
            
            # Insert results
            for student in students:
                status = "Active" if student.is_active else "Inactive"
                balance = student.balance
                balance_display = f"${balance:,.2f} ✗" if balance > 0 else f"${abs(balance):,.2f} ✓"
                
                self.students_tree.insert('', 'end', values=(
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
                ))
            
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
            # Get students by class
            students = Student.get_by_class(selected_class)
            
            # Insert into treeview
            for student in students:
                status = "Active" if student.is_active else "Inactive"
                balance = student.balance
                balance_display = f"${balance:,.2f} ✗" if balance > 0 else f"${abs(balance):,.2f} ✓"
                
                self.students_tree.insert('', 'end', values=(
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
                ))
            
            # Update status
            count = len(students)
            self.status_label.config(text=f"Class {selected_class}: {count} student(s)")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to filter by class: {str(e)}")
    
    def add_student(self):
        """Open dialog to add new student"""
        dialog = StudentDialog(self.frame, title="Add New Student")
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