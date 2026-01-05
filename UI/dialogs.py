"""
Dialog boxes for the School Management System
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, time
from typing import Optional, Dict, Any
import config
from models.student import Student
from models.teacher import Teacher
from models.finance import FeeType, FeePayment

class BaseDialog:
    """Base class for all dialogs"""
    
    def __init__(self, parent, title, width=500, height=400):
        self.parent = parent
        self.title = title
        self.width = width
        self.height = height
        self.result = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{width}x{height}")
        self.dialog.resizable(False, False)
        
        # Center dialog
        self.center_dialog()
        
        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Bind escape key to close
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        
        # Create main frame
        self.main_frame = ttk.Frame(self.dialog, padding="20")
        self.main_frame.pack(fill='both', expand=True)
    
    def center_dialog(self):
        """Center dialog on screen"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_button_box(self, frame):
        """Create standard button box (OK/Cancel)"""
        button_frame = ttk.Frame(frame)
        button_frame.pack(side='bottom', fill='x', pady=(20, 0))
        
        ttk.Button(
            button_frame,
            text="OK",
            command=self.on_ok,
            style='Primary.TButton'
        ).pack(side='right', padx=(5, 0))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.on_cancel
        ).pack(side='right')
    
    def on_ok(self):
        """OK button handler - to be overridden"""
        self.result = True
        self.dialog.destroy()
    
    def on_cancel(self):
        """Cancel button handler"""
        self.result = False
        self.dialog.destroy()
    
    def show(self):
        """Show dialog and wait for result"""
        self.dialog.wait_window()
        return self.result


class StudentDialog(BaseDialog):
    """Dialog for adding/editing students"""
    
    def __init__(self, parent, title, student=None):
        super().__init__(parent, title, 500, 500)
        self.student = student
        self.setup_ui()
    
    def setup_ui(self):
        """Setup student dialog UI"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True)
        
        # Personal Info Tab
        personal_frame = ttk.Frame(notebook)
        notebook.add(personal_frame, text="Personal Info")
        self.setup_personal_info(personal_frame)
        
        # Contact Info Tab
        contact_frame = ttk.Frame(notebook)
        notebook.add(contact_frame, text="Contact Info")
        self.setup_contact_info(contact_frame)
        
        # Academic Info Tab
        academic_frame = ttk.Frame(notebook)
        notebook.add(academic_frame, text="Academic Info")
        self.setup_academic_info(academic_frame)
        
        # Load data if editing
        if self.student:
            self.load_student_data()
        
        # Create button box
        self.create_button_box(self.main_frame)
    
    def setup_personal_info(self, parent):
        """Setup personal information fields"""
        # Form fields
        fields = [
            ("Student Code:", "student_code", "entry", 20),
            ("First Name*:", "first_name", "entry", 30),
            ("Last Name*:", "last_name", "entry", 30),
            ("Birth Date:", "birth_date", "entry", 15),
            ("Gender:", "gender", "combobox", ["Male", "Female", "Other"])
        ]
        
        self.widgets = {}
        
        for i, (label, field, widget_type, *args) in enumerate(fields):
            # Label
            ttk.Label(parent, text=label).grid(row=i, column=0, sticky='e', padx=(0, 10), pady=5)
            
            # Widget
            if widget_type == "entry":
                widget = ttk.Entry(parent, width=args[0])
                widget.grid(row=i, column=1, sticky='w', pady=5)
                
            elif widget_type == "combobox":
                widget = ttk.Combobox(parent, values=args[0], width=args[0] if len(args) > 1 else 20)
                widget.grid(row=i, column=1, sticky='w', pady=5)
            
            self.widgets[field] = widget
    
    def setup_contact_info(self, parent):
        """Setup contact information fields"""
        fields = [
            ("Parent/Guardian Name*:", "parent_name", "entry", 40),
            ("Parent Phone*:", "parent_phone", "entry", 20),
            ("Parent Email:", "parent_email", "entry", 40),
            ("Address:", "address", "text", 4, 40)
        ]
        
        for i, (label, field, widget_type, *args) in enumerate(fields):
            # Label
            ttk.Label(parent, text=label).grid(row=i, column=0, sticky='ne', padx=(0, 10), pady=5)
            
            # Widget
            if widget_type == "entry":
                widget = ttk.Entry(parent, width=args[0])
                widget.grid(row=i, column=1, sticky='w', pady=5)
                
            elif widget_type == "text":
                widget = tk.Text(parent, height=args[0], width=args[1])
                widget.grid(row=i, column=1, sticky='w', pady=5)
                
                # Add scrollbar
                scrollbar = ttk.Scrollbar(parent, command=widget.yview)
                scrollbar.grid(row=i, column=2, sticky='ns')
                widget['yscrollcommand'] = scrollbar.set
            
            self.widgets[field] = widget
    
    def setup_academic_info(self, parent):
        """Setup academic information fields"""
        # Get class list
        try:
            from database.connection import db
            query = "SELECT DISTINCT class_name FROM classes ORDER BY class_name"
            results = db.execute_query(query, fetch=True)
            classes = [r['class_name'] for r in results] if results else []
        except:
            classes = []
        
        fields = [
            ("Class*:", "class_name", "combobox", classes, 20),
            ("Enrollment Date*:", "enrollment_date", "entry", 15),
            ("Status:", "is_active", "combobox", ["Active", "Inactive"], 10)
        ]
        
        for i, (label, field, widget_type, *args) in enumerate(fields):
            # Label
            ttk.Label(parent, text=label).grid(row=i, column=0, sticky='e', padx=(0, 10), pady=5)
            
            # Widget
            if widget_type == "entry":
                widget = ttk.Entry(parent, width=args[0])
                widget.grid(row=i, column=1, sticky='w', pady=5)
                
            elif widget_type == "combobox":
                widget = ttk.Combobox(parent, values=args[0], width=args[1])
                widget.grid(row=i, column=1, sticky='w', pady=5)
            
            self.widgets[field] = widget
        
        # Set default values
        self.widgets['enrollment_date'].insert(0, date.today().strftime('%Y-%m-%d'))
        self.widgets['is_active'].set("Active")
    
    def load_student_data(self):
        """Load student data into form"""
        if not self.student:
            return
        
        # Personal info
        self.widgets['student_code'].insert(0, self.student.student_code)
        self.widgets['first_name'].insert(0, self.student.first_name)
        self.widgets['last_name'].insert(0, self.student.last_name)
        
        if self.student.birth_date:
            self.widgets['birth_date'].insert(0, self.student.birth_date.strftime('%Y-%m-%d'))
        
        # Contact info
        if self.student.parent_name:
            self.widgets['parent_name'].insert(0, self.student.parent_name)
        if self.student.parent_phone:
            self.widgets['parent_phone'].insert(0, self.student.parent_phone)
        if self.student.address:
            self.widgets['address'].insert('1.0', self.student.address)
        
        # Academic info
        self.widgets['class_name'].set(self.student.class_name)
        
        if self.student.enrollment_date:
            self.widgets['enrollment_date'].insert(0, self.student.enrollment_date.strftime('%Y-%m-%d'))
        
        self.widgets['is_active'].set("Active" if self.student.is_active else "Inactive")
    
    def validate_input(self):
        """Validate form input"""
        # Required fields
        required_fields = ['first_name', 'last_name', 'parent_name', 'parent_phone', 'class_name']
        
        for field in required_fields:
            widget = self.widgets[field]
            value = ""
            
            if isinstance(widget, tk.Text):
                value = widget.get('1.0', tk.END).strip()
            else:
                value = widget.get().strip()
            
            if not value:
                messagebox.showerror("Validation Error", f"{field.replace('_', ' ').title()} is required")
                return False
        
        # Validate dates
        date_fields = ['birth_date', 'enrollment_date']
        for field in date_fields:
            value = self.widgets[field].get().strip()
            if value:
                try:
                    datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    messagebox.showerror("Validation Error", f"Invalid date format for {field}. Use YYYY-MM-DD")
                    return False
        
        # Validate phone
        phone = self.widgets['parent_phone'].get().strip()
        if phone and not self.validate_phone(phone):
            messagebox.showerror("Validation Error", "Invalid phone number format")
            return False
        
        return True
    
    def validate_phone(self, phone):
        """Validate phone number"""
        import re
        # Remove non-digits
        digits = re.sub(r'\D', '', phone)
        return len(digits) >= 10
    
    def get_student_data(self):
        """Get student data from form"""
        data = {}
        
        # Personal info
        data['student_code'] = self.widgets['student_code'].get().strip()
        data['first_name'] = self.widgets['first_name'].get().strip()
        data['last_name'] = self.widgets['last_name'].get().strip()
        data['birth_date'] = self.widgets['birth_date'].get().strip() or None
        data['gender'] = self.widgets['gender'].get().strip() or None
        
        # Contact info
        data['parent_name'] = self.widgets['parent_name'].get().strip()
        data['parent_phone'] = self.widgets['parent_phone'].get().strip()
        
        if 'parent_email' in self.widgets:
            data['parent_email'] = self.widgets['parent_email'].get().strip() or None
        
        if isinstance(self.widgets['address'], tk.Text):
            data['address'] = self.widgets['address'].get('1.0', tk.END).strip()
        else:
            data['address'] = self.widgets['address'].get().strip()
        
        # Academic info
        data['class_name'] = self.widgets['class_name'].get().strip()
        data['enrollment_date'] = self.widgets['enrollment_date'].get().strip()
        data['is_active'] = self.widgets['is_active'].get() == "Active"
        
        return data
    
    def on_ok(self):
        """Save student data"""
        if not self.validate_input():
            return
        
        try:
            student_data = self.get_student_data()
            
            if self.student:
                # Update existing student
                success, message = StudentManager.update_student(self.student.student_id, student_data)
            else:
                # Add new student
                success, message, student = StudentManager.create_student(student_data)
            
            if success:
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save student: {str(e)}")


class TeacherDialog(BaseDialog):
    """Dialog for adding/editing teachers"""
    
    def __init__(self, parent, title, teacher=None):
        super().__init__(parent, title, 450, 400)
        self.teacher = teacher
        self.setup_ui()
    
    def setup_ui(self):
        """Setup teacher dialog UI"""
        # Form fields
        fields = [
            ("Teacher Code:", "teacher_code", "entry", 20),
            ("First Name*:", "first_name", "entry", 30),
            ("Last Name*:", "last_name", "entry", 30),
            ("Specialization:", "specialization", "entry", 40),
            ("Phone:", "phone", "entry", 20),
            ("Email:", "email", "entry", 40),
            ("Hire Date*:", "hire_date", "entry", 15),
            ("Status:", "is_active", "combobox", ["Active", "Inactive"], 10)
        ]
        
        self.widgets = {}
        
        for i, (label, field, widget_type, *args) in enumerate(fields):
            # Label
            ttk.Label(self.main_frame, text=label).grid(row=i, column=0, sticky='e', padx=(0, 10), pady=5)
            
            # Widget
            if widget_type == "entry":
                widget = ttk.Entry(self.main_frame, width=args[0])
                widget.grid(row=i, column=1, sticky='w', pady=5)
                
            elif widget_type == "combobox":
                widget = ttk.Combobox(self.main_frame, values=args[0], width=args[1])
                widget.grid(row=i, column=1, sticky='w', pady=5)
            
            self.widgets[field] = widget
        
        # Set default values
        self.widgets['hire_date'].insert(0, date.today().strftime('%Y-%m-%d'))
        self.widgets['is_active'].set("Active")
        
        # Load data if editing
        if self.teacher:
            self.load_teacher_data()
        
        # Create button box
        self.create_button_box(self.main_frame)
    
    def load_teacher_data(self):
        """Load teacher data into form"""
        if not self.teacher:
            return
        
        self.widgets['teacher_code'].insert(0, self.teacher.teacher_code)
        self.widgets['first_name'].insert(0, self.teacher.first_name)
        self.widgets['last_name'].insert(0, self.teacher.last_name)
        
        if self.teacher.subject_specialization:
            self.widgets['specialization'].insert(0, self.teacher.subject_specialization)
        if self.teacher.phone:
            self.widgets['phone'].insert(0, self.teacher.phone)
        if self.teacher.email:
            self.widgets['email'].insert(0, self.teacher.email)
        
        if self.teacher.hire_date:
            self.widgets['hire_date'].insert(0, self.teacher.hire_date.strftime('%Y-%m-%d'))
        
        self.widgets['is_active'].set("Active" if self.teacher.is_active else "Inactive")
    
    def validate_input(self):
        """Validate form input"""
        # Required fields
        required_fields = ['first_name', 'last_name', 'hire_date']
        
        for field in required_fields:
            value = self.widgets[field].get().strip()
            if not value:
                messagebox.showerror("Validation Error", f"{field.replace('_', ' ').title()} is required")
                return False
        
        # Validate date
        hire_date = self.widgets['hire_date'].get().strip()
        try:
            datetime.strptime(hire_date, '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid date format. Use YYYY-MM-DD")
            return False
        
        # Validate email if provided
        email = self.widgets['email'].get().strip()
        if email and '@' not in email:
            messagebox.showerror("Validation Error", "Invalid email address")
            return False
        
        return True
    
    def get_teacher_data(self):
        """Get teacher data from form"""
        data = {}
        
        data['teacher_code'] = self.widgets['teacher_code'].get().strip()
        data['first_name'] = self.widgets['first_name'].get().strip()
        data['last_name'] = self.widgets['last_name'].get().strip()
        data['subject_specialization'] = self.widgets['specialization'].get().strip() or None
        data['phone'] = self.widgets['phone'].get().strip() or None
        data['email'] = self.widgets['email'].get().strip() or None
        data['hire_date'] = self.widgets['hire_date'].get().strip()
        data['is_active'] = self.widgets['is_active'].get() == "Active"
        
        return data
    
    def on_ok(self):
        """Save teacher data"""
        if not self.validate_input():
            return
        
        try:
            teacher_data = self.get_teacher_data()
            
            if self.teacher:
                # Update existing teacher
                self.teacher.first_name = teacher_data['first_name']
                self.teacher.last_name = teacher_data['last_name']
                self.teacher.subject_specialization = teacher_data['subject_specialization']
                self.teacher.phone = teacher_data['phone']
                self.teacher.email = teacher_data['email']
                self.teacher.hire_date = datetime.strptime(teacher_data['hire_date'], '%Y-%m-%d').date()
                self.teacher.is_active = teacher_data['is_active']
                
                success, message = self.teacher.save()
            else:
                # Add new teacher
                teacher = Teacher.from_dict(teacher_data)
                success, message = teacher.save()
            
            if success:
                self.result = True
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save teacher: {str(e)}")


class FeePaymentDialog(BaseDialog):
    """Dialog for recording fee payments"""
    
    def __init__(self, parent, title, student, fee_summary):
        super().__init__(parent, title, 500, 450)
        self.student = student
        self.fee_summary = fee_summary
        self.setup_ui()
    
    def setup_ui(self):
        """Setup fee payment dialog UI"""
        # Student info frame
        info_frame = ttk.LabelFrame(self.main_frame, text="Student Information", padding="10")
        info_frame.pack(fill='x', pady=(0, 15))
        
        info_text = f"Name: {self.student.first_name} {self.student.last_name}\n"
        info_text += f"Class: {self.student.class_name}\n"
        info_text += f"Student Code: {self.student.student_code}"
        
        ttk.Label(info_frame, text=info_text).pack(anchor='w')
        
        # Fee summary frame
        summary_frame = ttk.LabelFrame(self.main_frame, text="Fee Summary", padding="10")
        summary_frame.pack(fill='x', pady=(0, 15))
        
        total_due = self.fee_summary.get('total_due', 0)
        total_paid = self.fee_summary.get('total_paid', 0)
        balance = self.fee_summary.get('total_balance', 0)
        
        summary_text = f"Total Due: ${total_due:,.2f}\n"
        summary_text += f"Total Paid: ${total_paid:,.2f}\n"
        summary_text += f"Balance: ${balance:,.2f}"
        
        ttk.Label(summary_frame, text=summary_text).pack(anchor='w')
        
        # Payment details frame
        payment_frame = ttk.LabelFrame(self.main_frame, text="Payment Details", padding="10")
        payment_frame.pack(fill='x', pady=(0, 15))
        
        # Fee type selection
        ttk.Label(payment_frame, text="Fee Type*:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.fee_type_var = tk.StringVar()
        
        # Get fee types
        fee_types = FeeType.get_all()
        fee_choices = [f"{ft.fee_name} (${ft.amount:,.2f})" for ft in fee_types]
        
        self.fee_combo = ttk.Combobox(payment_frame, textvariable=self.fee_type_var, values=fee_choices, width=40)
        self.fee_combo.grid(row=0, column=1, sticky='w', pady=5)
        self.fee_combo.current(0) if fee_choices else None
        
        # Amount
        ttk.Label(payment_frame, text="Amount*:").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.amount_var = tk.StringVar()
        self.amount_entry = ttk.Entry(payment_frame, textvariable=self.amount_var, width=20)
        self.amount_entry.grid(row=1, column=1, sticky='w', pady=5)
        
        # Payment date
        ttk.Label(payment_frame, text="Payment Date*:").grid(row=2, column=0, sticky='e', padx=(0, 10), pady=5)
        self.date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        self.date_entry = ttk.Entry(payment_frame, textvariable=self.date_var, width=15)
        self.date_entry.grid(row=2, column=1, sticky='w', pady=5)
        
        # Payment method
        ttk.Label(payment_frame, text="Payment Method:").grid(row=3, column=0, sticky='e', padx=(0, 10), pady=5)
        self.method_var = tk.StringVar(value="Cash")
        method_combo = ttk.Combobox(payment_frame, textvariable=self.method_var, 
                                   values=["Cash", "M-Pesa", "Bank Transfer", "Check", "Other"], width=15)
        method_combo.grid(row=3, column=1, sticky='w', pady=5)
        
        # Receipt number
        ttk.Label(payment_frame, text="Receipt Number:").grid(row=4, column=0, sticky='e', padx=(0, 10), pady=5)
        self.receipt_entry = ttk.Entry(payment_frame, width=20)
        self.receipt_entry.grid(row=4, column=1, sticky='w', pady=5)
        
        # Description
        ttk.Label(payment_frame, text="Description:").grid(row=5, column=0, sticky='ne', padx=(0, 10), pady=5)
        self.desc_text = tk.Text(payment_frame, height=3, width=30)
        self.desc_text.grid(row=5, column=1, sticky='w', pady=5)
        
        # Create button box
        self.create_button_box(self.main_frame)
    
    def validate_input(self):
        """Validate payment input"""
        # Required fields
        if not self.fee_type_var.get():
            messagebox.showerror("Validation Error", "Fee type is required")
            return False
        
        if not self.amount_var.get():
            messagebox.showerror("Validation Error", "Amount is required")
            return False
        
        # Validate amount
        try:
            amount = float(self.amount_var.get())
            if amount <= 0:
                messagebox.showerror("Validation Error", "Amount must be greater than 0")
                return False
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid amount")
            return False
        
        # Validate date
        try:
            datetime.strptime(self.date_var.get(), '%Y-%m-%d')
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid date format. Use YYYY-MM-DD")
            return False
        
        return True
    
    def on_ok(self):
        """Process fee payment"""
        if not self.validate_input():
            return
        
        try:
            # Parse fee type
            fee_type_str = self.fee_type_var.get()
            fee_name = fee_type_str.split(' (')[0]
            
            # Get fee type ID
            fee_types = FeeType.get_all()
            fee_type = next((ft for ft in fee_types if ft.fee_name == fee_name), None)
            
            if not fee_type:
                messagebox.showerror("Error", "Fee type not found")
                return
            
            # Create payment record
            fee_payment = FeePayment(
                student_id=self.student.student_id,
                fee_type_id=fee_type.fee_type_id,
                amount_paid=float(self.amount_var.get()),
                payment_date=datetime.strptime(self.date_var.get(), '%Y-%m-%d').date(),
                payment_method=self.method_var.get(),
                receipt_number=self.receipt_entry.get().strip() or None,
                description=self.desc_text.get('1.0', tk.END).strip()
            )
            
            success, message = fee_payment.save()
            
            if success:
                self.result = True
                messagebox.showinfo("Success", message)
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to record payment: {str(e)}")


class StudentSelectionDialog(BaseDialog):
    """Dialog for selecting a student"""
    
    def __init__(self, parent):
        super().__init__(parent, "Select Student", 600, 400)
        self.selected_student_id = None
        self.selected_student_name = ""
        self.setup_ui()
    
    def setup_ui(self):
        """Setup student selection dialog UI"""
        # Search frame
        search_frame = ttk.Frame(self.main_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side='left', padx=(0, 5))
        
        search_btn = ttk.Button(
            search_frame,
            text="Search",
            command=self.search_students
        )
        search_btn.pack(side='left', padx=(0, 5))
        
        clear_btn = ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        )
        clear_btn.pack(side='left')
        
        # Bind Enter key to search
        search_entry.bind('<Return>', lambda e: self.search_students())
        
        # Student list treeview
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.pack(fill='both', expand=True)
        
        # Define columns
        columns = ('ID', 'Code', 'Name', 'Class')
        
        # Create treeview
        self.students_tree = ttk.Treeview(
            tree_frame, 
            columns=columns,
            show='headings',
            selectmode='browse',
            height=15
        )
        
        # Configure columns
        for col in columns:
            self.students_tree.heading(col, text=col)
            self.students_tree.column(col, width=100)
        
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
        
        # Bind double-click to select
        self.students_tree.bind('<Double-1>', lambda e: self.select_student_from_tree())
        
        # Load initial data
        self.load_students()
        
        # Create button box
        self.create_button_box(self.main_frame)
    
    def load_students(self):
        """Load students into treeview"""
        # Clear existing items
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        
        try:
            from models.student import Student
            students = Student.get_all()
            
            for student in students:
                self.students_tree.insert('', 'end', values=(
                    student.student_id,
                    student.student_code,
                    f"{student.first_name} {student.last_name}",
                    student.class_name
                ))
                
        except Exception as e:
            print(f"Error loading students: {e}")
    
    def search_students(self):
        """Search students"""
        search_term = self.search_var.get().strip()
        
        if not search_term:
            self.load_students()
            return
        
        # Clear existing items
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        
        try:
            from models.student import Student
            students = Student.search(search_term)
            
            for student in students:
                self.students_tree.insert('', 'end', values=(
                    student.student_id,
                    student.student_code,
                    f"{student.first_name} {student.last_name}",
                    student.class_name
                ))
                
        except Exception as e:
            print(f"Error searching students: {e}")
    
    def clear_search(self):
        """Clear search and reload all students"""
        self.search_var.set("")
        self.load_students()
    
    def select_student_from_tree(self):
        """Select student from treeview on double-click"""
        selected = self.students_tree.selection()
        
        if not selected:
            return
        
        item = selected[0]
        values = self.students_tree.item(item, 'values')
        
        self.selected_student_id = values[0]
        self.selected_student_name = values[2]
        
        self.on_ok()
    
    def on_ok(self):
        """Handle OK button"""
        # Check if student is selected
        if not self.selected_student_id:
            selected = self.students_tree.selection()
            if selected:
                item = selected[0]
                values = self.students_tree.item(item, 'values')
                self.selected_student_id = values[0]
                self.selected_student_name = values[2]
            else:
                messagebox.showwarning("No Selection", "Please select a student")
                return
        
        self.result = True
        self.dialog.destroy()


class AttendanceDialog(BaseDialog):
    """Dialog for editing attendance"""
    
    def __init__(self, parent, title, date, student_id, attendance_data=None):
        super().__init__(parent, title, 350, 250)
        self.date = date
        self.student_id = student_id
        self.attendance_data = attendance_data or {}
        self.setup_ui()
    
    def setup_ui(self):
        """Setup attendance dialog UI"""
        # Status selection
        ttk.Label(self.main_frame, text="Status*:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=10)
        self.status_var = tk.StringVar(value=self.attendance_data.get('status', 'Present'))
        
        status_frame = ttk.Frame(self.main_frame)
        status_frame.grid(row=0, column=1, sticky='w', pady=10)
        
        statuses = [("Present", 'P'), ("Absent", 'A'), ("Late", 'L'), ("Excused", 'E')]
        
        for i, (text, value) in enumerate(statuses):
            rb = ttk.Radiobutton(
                status_frame,
                text=text,
                variable=self.status_var,
                value=text
            )
            rb.grid(row=0, column=i, padx=(0, 10))
        
        # Time entries
        ttk.Label(self.main_frame, text="Check In:").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.check_in_var = tk.StringVar()
        
        check_in_entry = ttk.Entry(self.main_frame, textvariable=self.check_in_var, width=10)
        check_in_entry.grid(row=1, column=1, sticky='w', pady=5)
        
        ttk.Label(self.main_frame, text="(HH:MM)").grid(row=1, column=2, sticky='w', padx=(5, 0))
        
        ttk.Label(self.main_frame, text="Check Out:").grid(row=2, column=0, sticky='e', padx=(0, 10), pady=5)
        self.check_out_var = tk.StringVar()
        
        check_out_entry = ttk.Entry(self.main_frame, textvariable=self.check_out_var, width=10)
        check_out_entry.grid(row=2, column=1, sticky='w', pady=5)
        
        ttk.Label(self.main_frame, text="(HH:MM)").grid(row=2, column=2, sticky='w', padx=(5, 0))
        
        # Remarks
        ttk.Label(self.main_frame, text="Remarks:").grid(row=3, column=0, sticky='ne', padx=(0, 10), pady=5)
        self.remarks_text = tk.Text(self.main_frame, height=4, width=30)
        self.remarks_text.grid(row=3, column=1, columnspan=2, sticky='w', pady=5)
        
        # Load existing data
        if self.attendance_data:
            if self.attendance_data.get('check_in_time'):
                self.check_in_var.set(self.attendance_data['check_in_time'].strftime('%H:%M'))
            if self.attendance_data.get('check_out_time'):
                self.check_out_var.set(self.attendance_data['check_out_time'].strftime('%H:%M'))
            if self.attendance_data.get('remarks'):
                self.remarks_text.insert('1.0', self.attendance_data['remarks'])
        
        # Create button box
        self.create_button_box(self.main_frame)
    
    def validate_input(self):
        """Validate attendance input"""
        # Validate times if provided
        if self.check_in_var.get():
            try:
                datetime.strptime(self.check_in_var.get(), '%H:%M')
            except ValueError:
                messagebox.showerror("Validation Error", "Invalid check-in time format. Use HH:MM")
                return False
        
        if self.check_out_var.get():
            try:
                datetime.strptime(self.check_out_var.get(), '%H:%M')
            except ValueError:
                messagebox.showerror("Validation Error", "Invalid check-out time format. Use HH:MM")
                return False
        
        # Check that check-out is after check-in
        if self.check_in_var.get() and self.check_out_var.get():
            check_in = datetime.strptime(self.check_in_var.get(), '%H:%M').time()
            check_out = datetime.strptime(self.check_out_var.get(), '%H:%M').time()
            
            if check_out <= check_in:
                messagebox.showerror("Validation Error", "Check-out time must be after check-in time")
                return False
        
        return True
    
    def on_ok(self):
        """Save attendance changes"""
        if not self.validate_input():
            return
        
        self.result = True
        self.dialog.destroy()


class ConfirmationDialog:
    """Simple confirmation dialog"""
    
    def __init__(self, parent, title, message, warning=None):
        self.parent = parent
        self.title = title
        self.message = message
        self.warning = warning
        self.result = False
    
    def show(self):
        """Show confirmation dialog"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(self.title)
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Make dialog modal
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Message
        message_frame = ttk.Frame(dialog, padding="20")
        message_frame.pack(fill='both', expand=True)
        
        ttk.Label(message_frame, text=self.message, wraplength=350, justify='left').pack(pady=(0, 10))
        
        if self.warning:
            ttk.Label(message_frame, text=self.warning, foreground='red', wraplength=350, justify='left').pack()
        
        # Buttons
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill='x', side='bottom')
        
        def on_yes():
            self.result = True
            dialog.destroy()
        
        def on_no():
            self.result = False
            dialog.destroy()
        
        ttk.Button(button_frame, text="Yes", command=on_yes, style='Danger.TButton').pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="No", command=on_no).pack(side='right')
        
        # Bind escape key to No
        dialog.bind('<Escape>', lambda e: on_no())
        
        dialog.wait_window()
        return self.result


class PreferencesDialog(BaseDialog):
    """Dialog for application preferences"""
    
    def __init__(self, parent):
        super().__init__(parent, "Preferences", 400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup preferences UI"""
        # Database settings
        db_frame = ttk.LabelFrame(self.main_frame, text="Database Settings", padding="10")
        db_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(db_frame, text="Host:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.host_var = tk.StringVar(value=config.Config.DB_CONFIG['host'])
        ttk.Entry(db_frame, textvariable=self.host_var, width=25).grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(db_frame, text="Username:").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.user_var = tk.StringVar(value=config.Config.DB_CONFIG['user'])
        ttk.Entry(db_frame, textvariable=self.user_var, width=25).grid(row=1, column=1, sticky='w', pady=5)
        
        ttk.Label(db_frame, text="Password:").grid(row=2, column=0, sticky='e', padx=(0, 10), pady=5)
        self.pass_var = tk.StringVar(value=config.Config.DB_CONFIG['password'])
        ttk.Entry(db_frame, textvariable=self.pass_var, width=25, show="*").grid(row=2, column=1, sticky='w', pady=5)
        
        ttk.Label(db_frame, text="Database:").grid(row=3, column=0, sticky='e', padx=(0, 10), pady=5)
        self.db_var = tk.StringVar(value=config.Config.DB_CONFIG['database'])
        ttk.Entry(db_frame, textvariable=self.db_var, width=25).grid(row=3, column=1, sticky='w', pady=5)
        
        # UI settings
        ui_frame = ttk.LabelFrame(self.main_frame, text="Interface Settings", padding="10")
        ui_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(ui_frame, text="Theme:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.theme_var = tk.StringVar(value=config.Config.UI['theme'])
        ttk.Combobox(ui_frame, textvariable=self.theme_var, 
                    values=['clam', 'alt', 'default', 'classic'], width=20).grid(row=0, column=1, sticky='w', pady=5)
        
        # Create button box
        self.create_button_box(self.main_frame)
    
    def on_ok(self):
        """Save preferences"""
        # Update config
        config.Config.DB_CONFIG['host'] = self.host_var.get()
        config.Config.DB_CONFIG['user'] = self.user_var.get()
        config.Config.DB_CONFIG['password'] = self.pass_var.get()
        config.Config.DB_CONFIG['database'] = self.db_var.get()
        config.Config.UI['theme'] = self.theme_var.get()
        
        # Save to file (would need implementation)
        # self.save_config_to_file()
        
        messagebox.showinfo("Success", "Preferences saved. Restart application for changes to take effect.")
        
        self.result = True
        self.dialog.destroy()
    
    def save_config_to_file(self):
        """Save config to file (implementation would write to config.py)"""
        # This is a placeholder - in production, you'd want to write to a config file
        pass


class AboutDialog(BaseDialog):
    """About dialog"""
    
    def __init__(self, parent):
        super().__init__(parent, "About", 400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup about dialog UI"""
        # Application info
        info_text = f"{config.Config.APP_NAME}\n"
        info_text += f"Version {config.Config.VERSION}\n\n"
        info_text += f"School: {config.Config.SCHOOL_NAME}\n"
        info_text += f"Address: {config.Config.SCHOOL_ADDRESS}\n"
        info_text += f"Phone: {config.Config.SCHOOL_PHONE}\n"
        info_text += f"Email: {config.Config.SCHOOL_EMAIL}\n\n"
        info_text += "© 2024 School Administration\n"
        info_text += "All rights reserved."
        
        ttk.Label(self.main_frame, text=info_text, justify='center').pack(expand=True, pady=20)
        
        # Close button
        ttk.Button(self.main_frame, text="Close", command=self.on_ok).pack(pady=10)
    
    def on_ok(self):
        """Close dialog"""
        self.result = True
        self.dialog.destroy()


class DateRangeDialog(BaseDialog):
    """Dialog for selecting a date range"""

    def __init__(self, parent, title="Select Date Range"):
        super().__init__(parent, title, 360, 180)
        self.start_date = None
        self.end_date = None
        self.setup_ui()

    def setup_ui(self):
        frame = ttk.Frame(self.main_frame)
        frame.pack(fill='both', expand=True, pady=10)

        ttk.Label(frame, text='Start Date (YYYY-MM-DD):').grid(row=0, column=0, sticky='e', padx=(0,8), pady=8)
        self.start_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.start_var, width=20).grid(row=0, column=1, sticky='w')

        ttk.Label(frame, text='End Date (YYYY-MM-DD):').grid(row=1, column=0, sticky='e', padx=(0,8), pady=8)
        self.end_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.end_var, width=20).grid(row=1, column=1, sticky='w')

        # Defaults
        today = date.today().strftime('%Y-%m-%d')
        self.start_var.set(today)
        self.end_var.set(today)

        self.create_button_box(self.main_frame)

    def validate_input(self):
        from datetime import datetime
        try:
            s = datetime.strptime(self.start_var.get().strip(), '%Y-%m-%d').date()
            e = datetime.strptime(self.end_var.get().strip(), '%Y-%m-%d').date()
            if s > e:
                messagebox.showerror('Validation Error', 'Start date must be before end date')
                return False
            self.start_date = s
            self.end_date = e
            return True
        except Exception:
            messagebox.showerror('Validation Error', 'Invalid date format. Use YYYY-MM-DD')
            return False

    def on_ok(self):
        if not self.validate_input():
            return
        self.result = True
        self.dialog.destroy()