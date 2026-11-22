"""
Dialog boxes for the School Management System
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date, time
from typing import Optional, Dict, Any
import config
from models.student import Student, StudentManager
from models.teacher import Teacher, TeacherManager
from models.finance import FeeType, FeePayment
from utils.helpers import format_currency, parse_currency

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
        # Allow vertical resizing so dialogs that are content-heavy don't clip buttons
        self.dialog.resizable(False, True)
        
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
        # Decide whether to attach to the provided frame or the top-level dialog.
        # If the provided frame already uses grid (has grid slaves), place the
        # button frame using grid to avoid pack/grid conflicts. Otherwise,
        # attach to the dialog root and pack.
        try:
            uses_grid = len(frame.grid_slaves()) > 0
        except Exception:
            uses_grid = False

        if uses_grid:
            button_frame = ttk.Frame(frame)
            # Place at the next available row at the bottom
            next_row = frame.grid_size()[1]
            button_frame.grid(row=next_row, column=0, columnspan=99, sticky='ew', pady=(20, 0))
        else:
            button_frame = ttk.Frame(self.dialog)
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
            ("Status:", "is_active", "combobox", ["Active", "Inactive"], 10),
            ("New Student:", "is_new", "checkbox", None)
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
            elif widget_type == "checkbox":
                var = tk.BooleanVar(value=True)
                widget = ttk.Checkbutton(parent, variable=var, text='Is New Student')
                widget.var = var
                widget.grid(row=i, column=1, sticky='w', pady=5)
            
            self.widgets[field] = widget
        
        # Set default values
        self.widgets['enrollment_date'].insert(0, date.today().strftime('%Y-%m-%d'))
        self.widgets['is_active'].set("Active")
        # default for new student
        try:
            if 'is_new' in self.widgets:
                # default True for new student when creating
                self.widgets['is_new'].var.set(True)
        except Exception:
            pass
    
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
        if getattr(self.student, 'parent_email', None):
            self.widgets['parent_email'].insert(0, self.student.parent_email)
        if self.student.address:
            self.widgets['address'].insert('1.0', self.student.address)
        
        # Academic info
        self.widgets['class_name'].set(self.student.class_name)
        
        if self.student.enrollment_date:
            self.widgets['enrollment_date'].insert(0, self.student.enrollment_date.strftime('%Y-%m-%d'))
        
        self.widgets['is_active'].set("Active" if self.student.is_active else "Inactive")
        try:
            if 'is_new' in self.widgets:
                self.widgets['is_new'].var.set(bool(getattr(self.student, 'is_new', True)))
        except Exception:
            pass
    
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
        
        # Contact info
        data['parent_name'] = self.widgets['parent_name'].get().strip()
        data['parent_phone'] = self.widgets['parent_phone'].get().strip()
        
        # Parent email is collected and will be passed to the Student model
        # now that the schema and model include `parent_email`.
        data['parent_email'] = self.widgets['parent_email'].get().strip()
        
        if isinstance(self.widgets['address'], tk.Text):
            data['address'] = self.widgets['address'].get('1.0', tk.END).strip()
        else:
            data['address'] = self.widgets['address'].get().strip()
        
        # Academic info
        data['class_name'] = self.widgets['class_name'].get().strip()
        data['enrollment_date'] = self.widgets['enrollment_date'].get().strip()
        data['is_active'] = self.widgets['is_active'].get() == "Active"
        # New student flag (checkbox)
        if 'is_new' in self.widgets:
            try:
                data['is_new'] = bool(self.widgets['is_new'].var.get())
            except Exception:
                data['is_new'] = True
        else:
            data['is_new'] = True
        
        return data
    
    def on_ok(self):
        """Save student data"""
        if not self.validate_input():
            return
        
        try:
            student_data = self.get_student_data()
            # If a Student object with an id was provided, treat as update.
            if self.student and getattr(self.student, 'student_id', None):
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


class StudentPreviewDialog(BaseDialog):
    """Read-only preview of a student's full information: personal, parent, finance."""

    def __init__(self, parent, title, student: Student):
        super().__init__(parent, title, 750, 600)
        self.student = student
        self.setup_ui()

    def setup_ui(self):
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(fill='both', expand=True)

        # Summary tab
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text='Summary')
        self._build_summary_tab(summary_frame)

        # Parent info tab
        parent_frame = ttk.Frame(notebook)
        notebook.add(parent_frame, text='Parent / Contact')
        self._build_parent_tab(parent_frame)

        # Finance & Payments tabs: only show if user has permission to view student finances
        if config.Config.has_permission('student_finance'):
            finance_frame = ttk.Frame(notebook)
            notebook.add(finance_frame, text='Finance')
            self._build_finance_tab(finance_frame)

            # Payment history tab
            payments_frame = ttk.Frame(notebook)
            notebook.add(payments_frame, text='Payments')
            self._build_payments_tab(payments_frame)

        # OK button only
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(side='bottom', fill='x', pady=(10,10))
        ttk.Button(btn_frame, text='Close', command=self.dialog.destroy).pack(side='right', padx=10)

    def _build_summary_tab(self, parent):
        s = self.student
        rows = [
            ('Student Code', getattr(s, 'student_code', '')),
            ('Name', f"{s.first_name} {s.last_name}"),
            ('Class', getattr(s, 'class_name', '')),
            ('Enrollment Date', s.enrollment_date.strftime('%Y-%m-%d') if getattr(s, 'enrollment_date', None) else ''),
            ('Birth Date', s.birth_date.strftime('%Y-%m-%d') if getattr(s, 'birth_date', None) else ''),
            ('Status', 'Active' if getattr(s, 'is_active', True) else 'Inactive')
        ]

        for i, (label, val) in enumerate(rows):
            ttk.Label(parent, text=label+':', font=('TkDefaultFont', 10, 'bold')).grid(row=i, column=0, sticky='e', padx=(10,8), pady=6)
            ttk.Label(parent, text=val).grid(row=i, column=1, sticky='w', padx=(0,10), pady=6)

    def _build_parent_tab(self, parent):
        s = self.student
        rows = [
            ('Parent/Guardian', s.parent_name or ''),
            ('Phone', s.parent_phone or ''),
            ('Email', getattr(s, 'parent_email', '') or ''),
            ('Address', s.address or '')
        ]

        for i, (label, val) in enumerate(rows):
            ttk.Label(parent, text=label+':', font=('TkDefaultFont', 10, 'bold')).grid(row=i, column=0, sticky='ne', padx=(10,8), pady=6)
            if label == 'Address':
                txt = tk.Text(parent, height=4, width=60)
                txt.insert('1.0', val)
                txt.configure(state='disabled')
                txt.grid(row=i, column=1, sticky='w', padx=(0,10), pady=6)
            else:
                ttk.Label(parent, text=val).grid(row=i, column=1, sticky='w', padx=(0,10), pady=6)

    def _build_finance_tab(self, parent):
        # Fetch summary via StudentManager
        try:
            summary = StudentManager.get_student_financial_summary(self.student.student_id)
        except Exception as e:
            print(f"Error fetching financial summary for student {self.student.student_id}: {e}")
            summary = {}

        # Totals header
        totals_frame = ttk.Frame(parent)
        totals_frame.pack(fill='x', padx=8, pady=(8,4))
        total_due = summary.get('total_due', 0.0)
        total_paid = summary.get('total_paid', 0.0)
        balance = summary.get('balance', 0.0)

        ttk.Label(totals_frame, text='Total Due:', font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, sticky='e')
        ttk.Label(totals_frame, text=format_currency(total_due)).grid(row=0, column=1, sticky='w', padx=6)
        ttk.Label(totals_frame, text='Total Paid:', font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=2, sticky='e', padx=(20,0))
        ttk.Label(totals_frame, text=format_currency(total_paid)).grid(row=0, column=3, sticky='w', padx=6)
        ttk.Label(totals_frame, text='Balance:', font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=4, sticky='e', padx=(20,0))
        ttk.Label(totals_frame, text=format_currency(balance)).grid(row=0, column=5, sticky='w', padx=6)

        # Fee details tree
        columns = ('Fee Type', 'Expected', 'Paid', 'Balance')
        tree = ttk.Treeview(parent, columns=columns, show='headings', height=10)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(fill='both', expand=True, padx=8, pady=8)

        for fd in summary.get('fee_details', []):
            tree.insert('', 'end', values=(
                fd.get('fee_name'),
                format_currency(fd.get('expected_amount', 0)),
                format_currency(fd.get('paid_amount', 0)),
                format_currency(fd.get('balance', 0))
            ))

    def _build_payments_tab(self, parent):
        try:
            history = StudentManager.get_payment_history(self.student.student_id)
        except Exception:
            history = []

        columns = ('Date', 'Fee', 'Amount', 'Method', 'Receipt')
        tree = ttk.Treeview(parent, columns=columns, show='headings', height=12)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.pack(fill='both', expand=True, padx=8, pady=8)

        for p in history:
            date_str = p.get('payment_date') if isinstance(p.get('payment_date'), str) else (p.get('payment_date').strftime('%Y-%m-%d') if p.get('payment_date') else '')
            tree.insert('', 'end', values=(
                date_str,
                p.get('fee_name', ''),
                format_currency(float(p.get('amount_paid', 0))),
                p.get('payment_method', ''),
                p.get('receipt_number', '')
            ))


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
            ("Salary Amount:", "salary_amount", "entry", 20),
            ("Allowance Amount:", "allowance_amount", "entry", 20),
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
        self.widgets['salary_amount'].insert(0, "0.00")
        self.widgets['allowance_amount'].insert(0, "0.00")
        # If editing an existing teacher, load their data into the form
        if self.teacher:
            try:
                # Map fields from Teacher model to dialog widgets
                self.widgets['teacher_code'].insert(0, getattr(self.teacher, 'teacher_code', '') or '')
                self.widgets['first_name'].insert(0, getattr(self.teacher, 'first_name', '') or '')
                self.widgets['last_name'].insert(0, getattr(self.teacher, 'last_name', '') or '')
                self.widgets['specialization'].insert(0, getattr(self.teacher, 'subject_specialization', '') or '')
                self.widgets['phone'].insert(0, getattr(self.teacher, 'phone', '') or '')
                self.widgets['email'].insert(0, getattr(self.teacher, 'email', '') or '')
                if getattr(self.teacher, 'hire_date', None):
                    try:
                        self.widgets['hire_date'].delete(0, tk.END)
                        self.widgets['hire_date'].insert(0, self.teacher.hire_date.strftime('%Y-%m-%d'))
                    except Exception:
                        pass
                # Salary amount
                salary = getattr(self.teacher, 'salary_amount', 0) or 0
                self.widgets['salary_amount'].delete(0, tk.END)
                self.widgets['salary_amount'].insert(0, str(salary))
                # Allowance amount
                allowance = getattr(self.teacher, 'allowance_amount', 0) or 0
                self.widgets['allowance_amount'].delete(0, tk.END)
                self.widgets['allowance_amount'].insert(0, str(allowance))
                # Status combobox expects 'Active'/'Inactive'
                try:
                    self.widgets['is_active'].set('Active' if getattr(self.teacher, 'is_active', True) else 'Inactive')
                except Exception:
                    pass
            except Exception:
                pass
        # Add dialog buttons (OK / Cancel)
        self.create_button_box(self.main_frame)

    def on_ok(self):
        """Save or update teacher record"""
        # Basic validation
        first_name = self.widgets['first_name'].get().strip()
        last_name = self.widgets['last_name'].get().strip()
        hire_date = self.widgets['hire_date'].get().strip()

        if not first_name or not last_name or not hire_date:
            messagebox.showerror("Validation Error", "First name, Last name and Hire date are required")
            return

        try:
            teacher_data = {
                'teacher_code': self.widgets['teacher_code'].get().strip(),
                'first_name': first_name,
                'last_name': last_name,
                'phone': self.widgets['phone'].get().strip(),
                'email': self.widgets['email'].get().strip(),
                'subject_specialization': self.widgets.get('specialization').get().strip(),
                'hire_date': hire_date,
                'salary_amount': float(self.widgets['salary_amount'].get().strip() or 0.0),
                'allowance_amount': float(self.widgets['allowance_amount'].get().strip() or 0.0),
                'is_active': self.widgets['is_active'].get() == 'Active'
            }

            if self.teacher:
                # Update existing
                success, message = TeacherManager.update_teacher(self.teacher.teacher_id, teacher_data)
                if success:
                    self.result = True
                    messagebox.showinfo("Success", message)
                    self.dialog.destroy()
                else:
                    messagebox.showerror("Error", message)
            else:
                # Create new
                success, message, teacher = TeacherManager.create_teacher(teacher_data)
                if success:
                    self.result = True
                    messagebox.showinfo("Success", message)
                    self.dialog.destroy()
                else:
                    messagebox.showerror("Error", message)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save teacher: {str(e)}")


class FeeTypeDialog(BaseDialog):
    """Dialog to add/edit a fee type"""
    def __init__(self, parent, title, fee_type=None):
        super().__init__(parent, title, 420, 320)
        self.fee_type = fee_type or {}
        self.result_data = None
        self.setup_ui()

    def setup_ui(self):
        frame = self.main_frame
        # Fee name
        ttk.Label(frame, text="Fee Name:").grid(row=0, column=0, sticky='e', padx=5, pady=8)
        self.name_var = tk.StringVar(value=self.fee_type.get('fee_name', ''))
        ttk.Entry(frame, textvariable=self.name_var, width=30).grid(row=0, column=1, sticky='w', pady=8)

        # Amount
        ttk.Label(frame, text="Amount:").grid(row=1, column=0, sticky='e', padx=5, pady=8)
        self.amount_var = tk.StringVar(value=str(self.fee_type.get('amount', '')))
        ttk.Entry(frame, textvariable=self.amount_var, width=20).grid(row=1, column=1, sticky='w', pady=8)

        # Term
        ttk.Label(frame, text="Term:").grid(row=2, column=0, sticky='e', padx=5, pady=8)
        self.term_var = tk.StringVar(value=self.fee_type.get('term', ''))
        ttk.Entry(frame, textvariable=self.term_var, width=20).grid(row=2, column=1, sticky='w', pady=8)

        # Required
        self.req_var = tk.IntVar(value=1 if self.fee_type.get('is_required', True) else 0)
        ttk.Checkbutton(frame, text='Required', variable=self.req_var).grid(row=3, column=1, sticky='w', pady=8)

        # Apply to specific classes
        ttk.Label(frame, text="Apply To Classes:").grid(row=4, column=0, sticky='ne', padx=5, pady=8)
        # Fetch classes from DB; if none, fall back to distinct classes in students table
        try:
            from database.connection import db
            classes_res = db.execute_query("SELECT class_id, class_name FROM classes ORDER BY class_name", fetch=True)
            classes_list = [(r['class_id'], r['class_name']) for r in classes_res] if classes_res else []
            # Fallback: if classes table empty, try distinct values from students.class
            if not classes_list:
                try:
                    studs = db.execute_query("SELECT DISTINCT class FROM students WHERE class IS NOT NULL ORDER BY class", fetch=True)
                    if studs:
                        for s in studs:
                            cname = s.get('class')
                            if not cname:
                                continue
                            # ensure class exists in classes table
                            exist = db.execute_query("SELECT class_id FROM classes WHERE class_name=%s", (cname,), fetch=True)
                            if not exist:
                                try:
                                    db.execute_query("INSERT INTO classes (class_name, academic_year) VALUES (%s, %s)", (cname, config.Config.CURRENT_ACADEMIC_YEAR))
                                except Exception:
                                    pass
                        # requery classes table
                        classes_res = db.execute_query("SELECT class_id, class_name FROM classes ORDER BY class_name", fetch=True)
                        classes_list = [(r['class_id'], r['class_name']) for r in classes_res] if classes_res else []
                except Exception:
                    pass
        except Exception:
            classes_list = []

        # Build display -> id map; if id is missing (from students fallback) map to None
        self.class_ids_map = {}
        for cid, cname in classes_list:
            display = cname
            self.class_ids_map[display] = cid

        # Frame for listbox and scrollbar
        lb_frame = ttk.Frame(frame)
        lb_frame.grid(row=4, column=1, sticky='w', pady=8)

        self.apply_all_var = tk.IntVar(value=1 if not self.fee_type.get('class_ids') else 0)
        ttk.Checkbutton(frame, text='Apply to all classes', variable=self.apply_all_var).grid(row=5, column=1, sticky='w')

        # Use checkboxes for each class so multiple selections are obvious
        self.class_vars = {}
        check_frame = ttk.Frame(lb_frame)
        check_frame.pack(side='left', fill='both', expand=True)

        for cid, cname in classes_list:
            display = cname
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(check_frame, text=display, variable=var)
            cb.pack(anchor='w')
            self.class_vars[display] = var

        # Preselect classes if editing and mappings provided
        existing_class_ids = self.fee_type.get('class_ids') or []
        if existing_class_ids:
            self.apply_all_var.set(0)
            for name, var in self.class_vars.items():
                mapped = self.class_ids_map.get(name)
                try:
                    if mapped and int(mapped) in existing_class_ids:
                        var.set(True)
                except Exception:
                    pass

        self.create_button_box(frame)

    def on_ok(self):
        # Basic validation
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror('Validation', 'Fee name is required')
            return
        try:
            amount = float(self.amount_var.get().strip()) if self.amount_var.get().strip() else 0.0
        except Exception:
            messagebox.showerror('Validation', 'Invalid amount')
            return

        term = config.Config.normalize_term_name(self.term_var.get().strip() or config.Config.CURRENT_TERM)
        is_required = bool(self.req_var.get())

        self.result_data = {
            'fee_name': name,
            'amount': amount,
            'term': term,
            'is_required': is_required
        }
        # classes selection
        apply_all = bool(self.apply_all_var.get())
        selected_ids = []
        selected_names = []
        if not apply_all:
            for name, var in (self.class_vars or {}).items():
                if var.get():
                    mapped = self.class_ids_map.get(name)
                    if mapped:
                        try:
                            selected_ids.append(int(mapped))
                            continue
                        except Exception:
                            pass
                    selected_names.append(name)
            if not selected_ids and not selected_names:
                messagebox.showerror('Validation', 'Select at least one class or enable "Apply to all classes".')
                return
        self.result_data['apply_to_all'] = apply_all
        self.result_data['class_ids'] = selected_ids
        self.result_data['class_names'] = selected_names
        self.result = True
        self.dialog.destroy()


class ExpenseCategoryDialog(BaseDialog):
    """Dialog to add/edit expense category"""
    def __init__(self, parent, title, category=None):
        super().__init__(parent, title, 380, 260)
        self.category = category or {}
        self.result_data = None
        self.setup_ui()

    def setup_ui(self):
        frame = self.main_frame
        ttk.Label(frame, text='Category Name:').grid(row=0, column=0, sticky='e', padx=5, pady=8)
        self.name_var = tk.StringVar(value=self.category.get('name', ''))
        ttk.Entry(frame, textvariable=self.name_var, width=30).grid(row=0, column=1, sticky='w', pady=8)

        ttk.Label(frame, text='Description:').grid(row=1, column=0, sticky='ne', padx=5, pady=8)
        self.desc_text = tk.Text(frame, height=5, width=30)
        self.desc_text.grid(row=1, column=1, sticky='w', pady=8)
        if self.category.get('description'):
            self.desc_text.insert('1.0', self.category.get('description'))

        self.create_button_box(frame)

    def on_ok(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror('Validation', 'Category name is required')
            return
        desc = self.desc_text.get('1.0', tk.END).strip()
        self.result_data = {'name': name, 'description': desc}
        self.result = True
        self.dialog.destroy()


class FeePaymentDialog(BaseDialog):
    """Dialog for recording or editing fee payments"""

    def __init__(self, parent, title, student, fee_summary, payment=None):
        super().__init__(parent, title, 500, 480)
        self.student = student
        self.fee_summary = fee_summary
        # Optional DB row/dict when editing an existing payment
        self.payment = payment
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
        
        summary_text = f"Total Due: {format_currency(total_due)}\n"
        summary_text += f"Total Paid: {format_currency(total_paid)}\n"
        summary_text += f"Balance: {format_currency(balance)}"
        
        ttk.Label(summary_frame, text=summary_text).pack(anchor='w')
        
        # Payment details frame
        payment_frame = ttk.LabelFrame(self.main_frame, text="Payment Details", padding="10")
        payment_frame.pack(fill='x', pady=(0, 15))
        
        # Fee type selection
        ttk.Label(payment_frame, text="Fee Type*:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.fee_type_var = tk.StringVar()
        
        # Get fee types applicable to student's class
        FeeType.ensure_carried_forward_fee_type(config.Config.CURRENT_ACADEMIC_YEAR, config.Config.CURRENT_TERM)
        fee_types = FeeType.get_applicable_for_class(
            getattr(self.student, 'class_name', ''),
            config.Config.CURRENT_ACADEMIC_YEAR,
            config.Config.CURRENT_TERM
        )

        # If student is continuing, registration and uniform should not be selectable
        filtered_fee_types = []
        for ft in fee_types:
            name_l = ft.fee_name.lower()
            if not getattr(self.student, 'is_new', True) and ('registration' in name_l or 'uniform' in name_l):
                continue
            filtered_fee_types.append(ft)

        def fee_choice_label(ft):
            amount = float(ft.amount or 0)
            if FeeType.is_carried_forward_fee_name(ft.fee_name):
                try:
                    from models.finance import FinancialManager

                    balance = FinancialManager.get_student_balance(
                        student_id=self.student.student_id,
                        academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
                        term=config.Config.CURRENT_TERM
                    )
                    amount = float(balance.get('remaining_carried_balance') or balance.get('carried_balance') or 0)
                except Exception:
                    amount = 0.0
            return f"{ft.fee_name} ({format_currency(amount)})"

        fee_choices = [fee_choice_label(ft) for ft in filtered_fee_types]

        self._fee_type_lookup = {fee_choice_label(ft): ft for ft in filtered_fee_types}

        self.fee_combo = ttk.Combobox(payment_frame, textvariable=self.fee_type_var, values=fee_choices, width=40)
        self.fee_combo.grid(row=0, column=1, sticky='w', pady=5)
        # If editing a payment, try to select the matching fee type; otherwise pick first
        if fee_choices:
            if getattr(self, 'payment', None):
                try:
                    target_fee = self.payment.get('fee_name') or self.payment.get('fee_type')
                    found = False
                    for k, ft in self._fee_type_lookup.items():
                        if ft.fee_name == target_fee:
                            self.fee_combo.set(k)
                            found = True
                            break
                    if not found:
                        self.fee_combo.current(0)
                except Exception:
                    self.fee_combo.current(0)
            else:
                self.fee_combo.current(0)
            # prefill amount for the selected fee
            self.on_fee_selected()
        # bind selection to auto-fill amount
        self.fee_combo.bind('<<ComboboxSelected>>', lambda e: self.on_fee_selected())
        
        # Amount
        ttk.Label(payment_frame, text="Amount*:").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.amount_var = tk.StringVar()
        self.amount_entry = ttk.Entry(payment_frame, textvariable=self.amount_var, width=20)
        self.amount_entry.grid(row=1, column=1, sticky='w', pady=5)

        # Payment date
        ttk.Label(payment_frame, text="Payment Date*: ").grid(row=2, column=0, sticky='e', padx=(0, 10), pady=5)
        self.date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        self.date_entry = ttk.Entry(payment_frame, textvariable=self.date_var, width=15)
        self.date_entry.grid(row=2, column=1, sticky='w', pady=5)

        # Payment method
        ttk.Label(payment_frame, text="Payment Method:").grid(row=3, column=0, sticky='e', padx=(0, 10), pady=5)
        self.method_var = tk.StringVar(value="Cash")
        method_combo = ttk.Combobox(payment_frame, textvariable=self.method_var, 
                                   values=["Cash", "Mobile money", "Bank Transfer", "Check", "Other"], width=15)
        method_combo.grid(row=3, column=1, sticky='w', pady=5)

        # Receipt number
        ttk.Label(payment_frame, text="Receipt Number:").grid(row=4, column=0, sticky='e', padx=(0, 10), pady=5)
        self.receipt_entry = ttk.Entry(payment_frame, width=20)
        self.receipt_entry.grid(row=4, column=1, sticky='w', pady=5)

        # Buttons specific to payment form (placed directly after receipt so they remain visible)
        btn_frame = ttk.Frame(payment_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        self.record_button = ttk.Button(btn_frame, text="Record Payment", command=self.on_ok)
        self.record_button.pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side='left')

        # Description (moved below buttons)
        ttk.Label(payment_frame, text="Description:").grid(row=6, column=0, sticky='ne', padx=(0, 10), pady=5)
        self.desc_text = tk.Text(payment_frame, height=3, width=30)
        self.desc_text.grid(row=6, column=1, sticky='w', pady=5)

        # Create standard dialog button box as well (OK/Cancel) for compatibility
        self.create_button_box(self.main_frame)

        # If editing, prefill values from provided payment row/dict
        if getattr(self, 'payment', None):
            try:
                # Amount
                amt = self.payment.get('amount_paid') or self.payment.get('amount') or 0
                try:
                    famt = float(amt)
                    self.amount_var.set(str(int(famt) if famt.is_integer() else f"{famt:.2f}"))
                except Exception:
                    self.amount_var.set(str(amt))
            except Exception:
                pass

            # Date
            try:
                pd = self.payment.get('payment_date')
                if pd:
                    if isinstance(pd, str):
                        self.date_var.set(pd.split('T')[0])
                    else:
                        self.date_var.set(pd.strftime('%Y-%m-%d'))
            except Exception:
                pass

            # Method, receipt, description
            try:
                if self.payment.get('payment_method'):
                    self.method_var.set(self.payment.get('payment_method'))
                if self.payment.get('receipt_number'):
                    self.receipt_entry.delete(0, tk.END)
                    self.receipt_entry.insert(0, self.payment.get('receipt_number'))
                if self.payment.get('description'):
                    self.desc_text.delete('1.0', tk.END)
                    self.desc_text.insert('1.0', self.payment.get('description'))
            except Exception:
                pass

            try:
                self.record_button.config(text='Update Payment')
            except Exception:
                pass

    def on_fee_selected(self):
        """Auto-fill amount when a fee type is selected; handle tuition overrides by class."""
        try:
            sel = self.fee_type_var.get()
            if not sel:
                return
            ft = self._fee_type_lookup.get(sel)
            if not ft:
                return
            fname = ft.fee_name.lower()
            if FeeType.is_carried_forward_fee_name(ft.fee_name):
                from models.finance import FinancialManager

                balance = FinancialManager.get_student_balance(
                    student_id=self.student.student_id,
                    academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
                    term=config.Config.CURRENT_TERM
                )
                amt = float(balance.get('remaining_carried_balance') or balance.get('carried_balance') or 0)
            # Tuition override by class
            elif 'tuition' in fname:
                cls = (getattr(self.student, 'class_name', '') or '').lower()
                if any(k in cls for k in ('nursery', 'reception')):
                    amt = 45000.0
                else:
                    amt = 85000.0
            else:
                amt = float(ft.amount)
            self.amount_var.set(str(int(amt) if float(amt).is_integer() else f"{amt:.2f}"))
        except Exception:
            pass
    
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
        # Handler invoked; proceed to validation and save

        if not self.validate_input():
            return

        try:
            # Resolve selected fee type directly from current lookup
            fee_type_str = self.fee_type_var.get()
            fee_type = self._fee_type_lookup.get(fee_type_str)

            if not fee_type:
                messagebox.showerror("Error", "Fee type not found")
                return

            # Create payment record (or update existing)
            fee_payment = FeePayment(
                student_id=self.student.student_id,
                fee_type_id=fee_type.fee_type_id,
                amount_paid=float(self.amount_var.get()),
                payment_date=datetime.strptime(self.date_var.get(), '%Y-%m-%d').date(),
                payment_method=self.method_var.get(),
                receipt_number=self.receipt_entry.get().strip() or None,
                description=self.desc_text.get('1.0', tk.END).strip()
            )

            # If editing an existing payment, set its id and call update()
            if getattr(self, 'payment', None) and self.payment.get('fee_id'):
                try:
                    fee_payment.fee_id = int(self.payment.get('fee_id'))
                except Exception:
                    fee_payment.fee_id = self.payment.get('fee_id')
                success, message = fee_payment.update()
            else:
                success, message = fee_payment.save()

            if success:
                # Notify application to refresh totals and views
                try:
                    root = self.dialog.nametowidget('.')  # main window, where app events are bound
                    root.event_generate("<<PaymentRecorded>>")
                except Exception:
                    pass

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


class UsersDialog(BaseDialog):
    """Dialog to manage application users and their roles"""
    def __init__(self, parent):
        super().__init__(parent, "Manage Users", 600, 400)
        self.setup_ui()

    def setup_ui(self):
        frame = self.main_frame
        # Users tree
        cols = ('Username', 'Role', 'Current')
        self.tree = ttk.Treeview(frame, columns=cols, show='headings', height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=150)
        self.tree.pack(fill='both', expand=True, pady=(0,10))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x')

        ttk.Button(btn_frame, text='Add User', command=self.add_user).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Change Password', command=self.change_password).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Edit Role', command=self.edit_role).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Remove User', command=self.remove_user).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Close', command=self.on_cancel).pack(side='right')

        self.load_users()

    def load_users(self):
        # clear
        for i in self.tree.get_children():
            self.tree.delete(i)
        users = config.Config.get_users()
        current = getattr(config.Config, 'CURRENT_USER', None)
        for uname, role in (users or {}).items():
            is_current = 'Yes' if current == uname else ''
            self.tree.insert('', 'end', values=(uname, role, is_current))

    def add_user(self):
        uname = simpledialog.askstring('Add User', 'Username:', parent=self.dialog)
        if not uname:
            return
        # choose role
        roles = list(config.Config.PERMISSIONS.keys())
        role = simpledialog.askstring('Role', f'Role for {uname} (options: {", ".join(roles)}):', parent=self.dialog)
        if not role:
            return
        if role not in roles:
            messagebox.showerror('Invalid Role', 'Role not recognized')
            return
        if not config.Config.has_users() and role != 'Administrator':
            messagebox.showerror('Invalid Role', 'The first user must be an Administrator.')
            return
        pwd = simpledialog.askstring('Password', f'Set password for {uname} (leave blank for none):', parent=self.dialog, show='*')
        if config.Config.add_user(uname, role, password=pwd):
            self.load_users()
            messagebox.showinfo('Success', f'User {uname} added with role {role}')
        else:
            messagebox.showerror('Error', 'Failed to add user')

    def edit_role(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('No Selection', 'Select a user to edit')
            return
        item = sel[0]
        uname, old_role, _ = self.tree.item(item, 'values')
        roles = list(config.Config.PERMISSIONS.keys())
        role = simpledialog.askstring('Edit Role', f'New role for {uname} (options: {", ".join(roles)}):', parent=self.dialog, initialvalue=old_role)
        if not role:
            return
        if role not in roles:
            messagebox.showerror('Invalid Role', 'Role not recognized')
            return
        if config.Config.would_remove_last_admin(uname, new_role=role):
            messagebox.showerror('Not Allowed', 'At least one Administrator must remain.')
            return
        if config.Config.set_user_role(uname, role):
            self.load_users()
            # If current user changed role, emit event
            try:
                root = self.dialog.nametowidget('.')  # main window, where app events are bound
                root.event_generate('<<UserRoleChanged>>')
            except Exception:
                pass
            messagebox.showinfo('Success', f'Updated {uname} to role {role}')
        else:
            messagebox.showerror('Error', 'Failed to update role')

    def remove_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('No Selection', 'Select a user to remove')
            return
        item = sel[0]
        uname = self.tree.item(item, 'values')[0]
        if config.Config.would_remove_last_admin(uname):
            messagebox.showerror('Not Allowed', 'At least one Administrator must remain while other users exist.')
            return
        if messagebox.askyesno('Confirm', f'Remove user {uname}?'):
            if config.Config.remove_user(uname):
                self.load_users()
                try:
                    self.dialog.nametowidget('.').event_generate('<<UserRoleChanged>>')
                except Exception:
                    pass
                messagebox.showinfo('Removed', f'User {uname} removed')
            else:
                messagebox.showerror('Error', 'Failed to remove user')

    def change_password(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('No Selection', 'Select a user to change password')
            return
        item = sel[0]
        uname = self.tree.item(item, 'values')[0]
        pwd = simpledialog.askstring('Set Password', f'Enter new password for {uname}:', parent=self.dialog, show='*')
        if pwd is None:
            return
        confirm = simpledialog.askstring('Confirm Password', f'Confirm new password for {uname}:', parent=self.dialog, show='*')
        if pwd != confirm:
            messagebox.showerror('Mismatch', 'Passwords do not match')
            return
        if config.Config.set_user_password(uname, pwd):
            messagebox.showinfo('Success', 'Password updated')
        else:
            messagebox.showerror('Error', 'Failed to update password')


class LoginDialog(BaseDialog):
    """Simple login dialog to pick an existing user"""
    def __init__(self, parent):
        super().__init__(parent, 'Login', 360, 180)
        self.setup_ui()

    def setup_ui(self):
        frame = self.main_frame
        ttk.Label(frame, text='Select User:').pack(anchor='w', pady=(6,4))
        users = list((config.Config.get_users() or {}).keys())
        self.user_var = tk.StringVar()
        self.combo = ttk.Combobox(frame, textvariable=self.user_var, values=users, width=30)
        self.combo.pack(anchor='w', pady=(0,8))
        if users:
            self.combo.current(0)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=(8,0))
        ttk.Button(btn_frame, text='Login', command=self.on_ok).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Cancel', command=self.on_cancel).pack(side='left')

    def on_ok(self):
        uname = self.user_var.get()
        if not uname:
            messagebox.showwarning('No User', 'Select a user to login')
            return

        info = config.Config.get_user_info(uname) or {}
        # If user has no password, offer to set one now
        if not info.get('password'):
            set_now = messagebox.askyesno('Set Password', f'User "{uname}" has no password. Set one now?')
            if set_now:
                pwd = simpledialog.askstring('Set Password', f'Enter new password for {uname}:', parent=self.dialog, show='*')
                if pwd is None:
                    return
                confirm = simpledialog.askstring('Confirm Password', f'Confirm new password for {uname}:', parent=self.dialog, show='*')
                if pwd != confirm:
                    messagebox.showerror('Mismatch', 'Passwords do not match')
                    return
                if not config.Config.set_user_password(uname, pwd):
                    messagebox.showerror('Error', 'Failed to set password')
                    return
            else:
                # allow login without password if user declines
                pass

        # If password is now set, require it
        info = config.Config.get_user_info(uname) or {}
        if info.get('password'):
            pwd = simpledialog.askstring('Password', f'Password for {uname}:', parent=self.dialog, show='*')
            if pwd is None:
                return
            if not config.Config.verify_user_credentials(uname, pwd):
                messagebox.showerror('Login Failed', 'Invalid credentials')
                return

        # Set current user
        if config.Config.set_current_user(uname):
            try:
                root = self.dialog.nametowidget('.')  # main window, where app events are bound
                root.event_generate('<<UserRoleChanged>>')
            except Exception:
                pass
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror('Login Failed', 'Failed to set current user')


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
        super().__init__(parent, "Preferences", 760, 760)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup preferences UI"""
        container = ttk.Frame(self.main_frame)
        container.pack(fill='both', expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        content_frame = ttk.Frame(canvas, padding=(0, 0, 12, 0))
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor='nw')

        def _update_scroll_region(event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))

        def _sync_canvas_width(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        content_frame.bind('<Configure>', _update_scroll_region)
        canvas.bind('<Configure>', _sync_canvas_width)

        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        self.dialog.bind('<Destroy>', lambda e: canvas.unbind_all('<MouseWheel>'))

        # Data storage
        db_frame = ttk.LabelFrame(content_frame, text="Data Storage", padding="10")
        db_frame.pack(fill='x', pady=(0, 10))
        self.host_var = self.user_var = self.pass_var = self.db_var = None

        if config.Config.DB_BACKEND == 'sqlite':
            data_file = config.Config.sqlite_path()
            ttk.Label(db_frame, text="School data is saved on this computer in:").grid(row=0, column=0, columnspan=2, sticky='w')
            ttk.Label(db_frame, text=str(data_file), foreground='#333').grid(row=1, column=0, columnspan=2, sticky='w', pady=(2, 6))
            ttk.Label(db_frame, text=f"Automatic daily backups are kept in:\n{config.Config.PATHS['backups']}",
                      foreground='#555').grid(row=2, column=0, sticky='w')

            def open_folder(path=data_file.parent):
                import os
                try:
                    os.startfile(str(path))
                except Exception as exc:
                    messagebox.showerror("Open Folder", str(exc), parent=self.dialog)
            ttk.Button(db_frame, text="Open data folder", command=open_folder).grid(row=2, column=1, sticky='e', padx=(16, 0))
        else:
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
        ui_frame = ttk.LabelFrame(content_frame, text="Interface Settings", padding="10")
        ui_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(ui_frame, text="Theme:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.theme_var = tk.StringVar(value=config.Config.UI['theme'])
        ttk.Combobox(ui_frame, textvariable=self.theme_var,
                    values=['clam', 'alt', 'default', 'classic'], width=20).grid(row=0, column=1, sticky='w', pady=5)

        self.require_login_var = tk.BooleanVar(value=bool(config.Config.REQUIRE_LOGIN))
        ttk.Checkbutton(ui_frame, text="Ask for a username and password when the program opens",
                        variable=self.require_login_var).grid(row=1, column=0, columnspan=2, sticky='w', pady=(8, 0))
        ttk.Label(ui_frame, text="Leave off on a computer only you use. Takes effect the next time the program starts.",
                  foreground='#555').grid(row=2, column=0, columnspan=2, sticky='w')

        # Academic configuration
        acad_frame = ttk.LabelFrame(content_frame, text="Academic Configuration", padding="10")
        acad_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(acad_frame, text="Academic Year:").grid(row=0, column=0, sticky='e', padx=(0,10), pady=5)
        self.acad_var = tk.StringVar(value=getattr(config.Config, 'CURRENT_ACADEMIC_YEAR', ''))
        ttk.Entry(acad_frame, textvariable=self.acad_var, width=20).grid(row=0, column=1, sticky='w', pady=5)

        ttk.Label(acad_frame, text="Academic Year Start:").grid(row=1, column=0, sticky='e', padx=(0,10), pady=5)
        self.acad_start_var = tk.StringVar(value=getattr(config.Config, 'ACADEMIC_YEAR_START_DATE', '') or '')
        ttk.Entry(acad_frame, textvariable=self.acad_start_var, width=20).grid(row=1, column=1, sticky='w', pady=5)

        ttk.Label(acad_frame, text="Academic Year End:").grid(row=1, column=2, sticky='e', padx=(10,10), pady=5)
        self.acad_end_var = tk.StringVar(value=getattr(config.Config, 'ACADEMIC_YEAR_END_DATE', '') or '')
        ttk.Entry(acad_frame, textvariable=self.acad_end_var, width=20).grid(row=1, column=3, sticky='w', pady=5)

        ttk.Label(acad_frame, text="Current Active Term:").grid(row=2, column=0, sticky='e', padx=(0,10), pady=5)
        self.current_term_var = tk.StringVar(value=getattr(config.Config, 'CURRENT_TERM', '') or '')
        current_term_combo = ttk.Combobox(
            acad_frame,
            textvariable=self.current_term_var,
            values=getattr(config.Config, 'TERMS', ['Term 1','Term 2','Term 3']),
            width=18,
            state='readonly'
        )
        current_term_combo.grid(row=2, column=1, sticky='w', pady=5)
        current_term_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_term_preview())

        ttk.Label(acad_frame, text="Current Term Start:").grid(row=2, column=2, sticky='e', padx=(10,10), pady=5)
        self.term_start_var = tk.StringVar(value=getattr(config.Config, 'TERM_START_DATE', '') or '')
        ttk.Entry(acad_frame, textvariable=self.term_start_var, width=20).grid(row=2, column=3, sticky='w', pady=5)

        ttk.Label(acad_frame, text="Current Term End:").grid(row=3, column=0, sticky='e', padx=(0,10), pady=5)
        self.term_end_var = tk.StringVar(value=getattr(config.Config, 'TERM_END_DATE', '') or '')
        ttk.Entry(acad_frame, textvariable=self.term_end_var, width=20).grid(row=3, column=1, sticky='w', pady=5)

        ttk.Label(acad_frame, text="Term Schedule:").grid(row=4, column=0, sticky='ne', padx=(0,10), pady=5)
        schedule_frame = ttk.Frame(acad_frame)
        schedule_frame.grid(row=4, column=1, columnspan=3, sticky='w', pady=5)
        ttk.Label(schedule_frame, text="Term", width=12).grid(row=0, column=0, sticky='w')
        ttk.Label(schedule_frame, text="Start Date", width=18).grid(row=0, column=1, sticky='w')
        ttk.Label(schedule_frame, text="End Date", width=18).grid(row=0, column=2, sticky='w')
        self.term_schedule_vars = {}
        existing_schedule = getattr(config.Config, 'TERM_SCHEDULE', {}) or {}
        for idx, term_name in enumerate(getattr(config.Config, 'TERMS', ['Term 1', 'Term 2', 'Term 3']), start=1):
            term_info = existing_schedule.get(term_name, {}) if isinstance(existing_schedule, dict) else {}
            start_var = tk.StringVar(value=term_info.get('start_date') or '')
            end_var = tk.StringVar(value=term_info.get('end_date') or '')
            self.term_schedule_vars[term_name] = {'start_var': start_var, 'end_var': end_var}
            ttk.Label(schedule_frame, text=term_name, width=12).grid(row=idx, column=0, sticky='w', pady=2)
            ttk.Entry(schedule_frame, textvariable=start_var, width=18).grid(row=idx, column=1, sticky='w', padx=(0, 8), pady=2)
            ttk.Entry(schedule_frame, textvariable=end_var, width=18).grid(row=idx, column=2, sticky='w', pady=2)

        preview_frame = ttk.LabelFrame(content_frame, text="Term Transition Preview", padding="10")
        preview_frame.pack(fill='x', pady=(0, 10))
        self.preview_from_term_var = tk.StringVar(value=getattr(config.Config, 'CURRENT_TERM', '') or '')
        self.preview_to_term_var = tk.StringVar(value=getattr(config.Config, 'CURRENT_TERM', '') or '')
        self.preview_students_var = tk.StringVar(value='0')
        self.preview_reset_var = tk.StringVar(value='0')
        self.preview_carry_var = tk.StringVar(value='0')
        self.preview_previous_total_var = tk.StringVar(value=format_currency(0))
        self.preview_opening_total_var = tk.StringVar(value=format_currency(0))
        self.preview_message_var = tk.StringVar(value='Changing the active term will show a preview here before confirmation.')

        ttk.Label(preview_frame, text="From Term:").grid(row=0, column=0, sticky='e', padx=(0, 8), pady=4)
        ttk.Label(preview_frame, textvariable=self.preview_from_term_var, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky='w', pady=4)
        ttk.Label(preview_frame, text="To Term:").grid(row=0, column=2, sticky='e', padx=(16, 8), pady=4)
        ttk.Label(preview_frame, textvariable=self.preview_to_term_var, font=('Arial', 10, 'bold')).grid(row=0, column=3, sticky='w', pady=4)
        ttk.Label(preview_frame, text="Students:").grid(row=1, column=0, sticky='e', padx=(0, 8), pady=4)
        ttk.Label(preview_frame, textvariable=self.preview_students_var).grid(row=1, column=1, sticky='w', pady=4)
        ttk.Label(preview_frame, text="Reset:").grid(row=1, column=2, sticky='e', padx=(16, 8), pady=4)
        ttk.Label(preview_frame, textvariable=self.preview_reset_var).grid(row=1, column=3, sticky='w', pady=4)
        ttk.Label(preview_frame, text="Carry Forward:").grid(row=2, column=0, sticky='e', padx=(0, 8), pady=4)
        ttk.Label(preview_frame, textvariable=self.preview_carry_var).grid(row=2, column=1, sticky='w', pady=4)
        ttk.Label(preview_frame, text="Prev Outstanding:").grid(row=2, column=2, sticky='e', padx=(16, 8), pady=4)
        ttk.Label(preview_frame, textvariable=self.preview_previous_total_var).grid(row=2, column=3, sticky='w', pady=4)
        ttk.Label(preview_frame, text="Opening Balance:").grid(row=3, column=0, sticky='e', padx=(0, 8), pady=4)
        ttk.Label(preview_frame, textvariable=self.preview_opening_total_var).grid(row=3, column=1, sticky='w', pady=4)
        ttk.Label(preview_frame, textvariable=self.preview_message_var, wraplength=620, justify='left').grid(row=4, column=0, columnspan=4, sticky='w', pady=(8, 0))

        # Previous period (read-only)
        prev_frame = ttk.LabelFrame(content_frame, text="Previous Period", padding="10")
        prev_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(prev_frame, text="Previous Academic Year:").grid(row=0, column=0, sticky='e', padx=(0, 10), pady=5)
        self.prev_acad_var = tk.StringVar(value=getattr(config.Config, 'PREVIOUS_ACADEMIC_YEAR', '') or '')
        ttk.Entry(prev_frame, textvariable=self.prev_acad_var, width=20, state='readonly').grid(row=0, column=1, sticky='w', pady=5)

        ttk.Label(prev_frame, text="Previous Term:").grid(row=1, column=0, sticky='e', padx=(0, 10), pady=5)
        self.prev_term_var = tk.StringVar(value=getattr(config.Config, 'PREVIOUS_TERM', '') or '')
        ttk.Entry(prev_frame, textvariable=self.prev_term_var, width=20, state='readonly').grid(row=1, column=1, sticky='w', pady=5)
        
        # Create button box
        self.create_button_box(self.main_frame)
        self.refresh_term_preview()

    def _sync_current_term_dates(self):
        """Sync current term date fields from the term schedule table."""
        term_name = (self.current_term_var.get() or '').strip()
        if not term_name:
            return
        term_vars = self.term_schedule_vars.get(term_name) or {}
        self.term_start_var.set(term_vars.get('start_var').get() if term_vars.get('start_var') else '')
        self.term_end_var.set(term_vars.get('end_var').get() if term_vars.get('end_var') else '')

    def _validate_date_string(self, value: str, label: str):
        """Validate optional YYYY-MM-DD date strings."""
        value = (value or '').strip()
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(f"{label} must be in YYYY-MM-DD format.")

    def _collect_term_schedule(self):
        """Collect term schedule values from the UI."""
        schedule = {}
        for term_name, vars_map in self.term_schedule_vars.items():
            schedule[term_name] = {
                'start_date': (vars_map['start_var'].get() or '').strip() or None,
                'end_date': (vars_map['end_var'].get() or '').strip() or None
            }
        selected_term = (self.current_term_var.get() or '').strip()
        if selected_term and selected_term in schedule:
            current_start = (self.term_start_var.get() or '').strip() or None
            current_end = (self.term_end_var.get() or '').strip() or None
            if current_start:
                schedule[selected_term]['start_date'] = current_start
            if current_end:
                schedule[selected_term]['end_date'] = current_end
        return schedule

    def _validate_academic_configuration(self):
        """Validate academic year and term date settings."""
        year_start = self._validate_date_string(self.acad_start_var.get(), "Academic Year Start")
        year_end = self._validate_date_string(self.acad_end_var.get(), "Academic Year End")
        if year_start and year_end and year_start > year_end:
            raise ValueError("Academic Year Start must be on or before Academic Year End.")

        schedule = self._collect_term_schedule()
        ordered_ranges = []
        for term_name in getattr(config.Config, 'TERMS', ['Term 1', 'Term 2', 'Term 3']):
            info = schedule.get(term_name, {})
            start_date = self._validate_date_string(info.get('start_date'), f"{term_name} Start Date")
            end_date = self._validate_date_string(info.get('end_date'), f"{term_name} End Date")
            if start_date and end_date and start_date > end_date:
                raise ValueError(f"{term_name} Start Date must be on or before {term_name} End Date.")
            if start_date and year_start and start_date < year_start:
                raise ValueError(f"{term_name} Start Date cannot be before the Academic Year Start.")
            if end_date and year_end and end_date > year_end:
                raise ValueError(f"{term_name} End Date cannot be after the Academic Year End.")
            if start_date and end_date:
                ordered_ranges.append((term_name, start_date, end_date))

        ordered_ranges.sort(key=lambda item: item[1])
        for idx in range(1, len(ordered_ranges)):
            prev_term, _, prev_end = ordered_ranges[idx - 1]
            term_name, start_date, _ = ordered_ranges[idx]
            if start_date < prev_end:
                raise ValueError(f"{term_name} starts before {prev_term} ends.")
        return schedule

    def _show_dates_for_year(self, year_changes: bool):
        """Blank last year's dates when the selected term opens a new academic year.

        Switching back to a same-year term restores the dates that were shown
        before they were blanked. Nothing changes while the state is unchanged,
        so dates typed by the user are kept.
        """
        if year_changes == getattr(self, '_dates_blanked', False):
            return
        if year_changes:
            self._original_dates = {
                'acad_start': self.acad_start_var.get(),
                'acad_end': self.acad_end_var.get(),
                'terms': {name: (v['start_var'].get(), v['end_var'].get())
                          for name, v in self.term_schedule_vars.items()},
            }
        self._dates_blanked = year_changes
        original = self._original_dates
        cutoff = config.Config.academic_year_date_cutoff() if year_changes else None

        def pick(value):
            parsed = config.Config.parse_config_date(value)
            return '' if (cutoff and parsed and parsed <= cutoff) else value

        self.acad_start_var.set(pick(original['acad_start']))
        self.acad_end_var.set(pick(original['acad_end']))
        for name, (start, end) in original['terms'].items():
            self.term_schedule_vars[name]['start_var'].set(pick(start))
            self.term_schedule_vars[name]['end_var'].set(pick(end))

    def refresh_term_preview(self):
        """Refresh the preview summary for the selected active term."""
        previous_acad = getattr(config.Config, 'CURRENT_ACADEMIC_YEAR', None)
        previous_term = getattr(config.Config, 'CURRENT_TERM', None)
        selected_term = (self.current_term_var.get() or '').strip() or previous_term
        self.preview_from_term_var.set(f"{previous_term} ({previous_acad})" if previous_term else '')
        self.preview_to_term_var.set(selected_term or '')
        self.preview_students_var.set('0')
        self.preview_reset_var.set('0')
        self.preview_carry_var.set('0')
        self.preview_previous_total_var.set(format_currency(0))
        self.preview_opening_total_var.set(format_currency(0))
        self._pending_rollover_preview = None

        if not previous_term or not previous_acad:
            self._sync_current_term_dates()
            self.preview_message_var.set("Set the initial active term here. Rollover preview becomes available after the first term is established.")
            return

        if not selected_term or selected_term == previous_term:
            self.acad_var.set(previous_acad)
            self._show_dates_for_year(False)
            self._sync_current_term_dates()
            self.preview_message_var.set("No term change pending. Updating dates here will not affect balances until the active term changes.")
            return

        from models.finance import FinancialManager
        try:
            to_year, to_term = FinancialManager._resolve_rollover_target(previous_acad, previous_term, selected_term)
        except ValueError as e:
            self.acad_var.set(previous_acad)
            self._show_dates_for_year(False)
            self._sync_current_term_dates()
            self.preview_message_var.set(str(e))
            return

        year_changes = to_year != previous_acad
        # The academic year follows from the term change; it is not typed in.
        self.acad_var.set(to_year)
        self._show_dates_for_year(year_changes)
        self._sync_current_term_dates()
        self.preview_to_term_var.set(f"{to_term} ({to_year})")

        try:
            preview = FinancialManager.get_term_rollover_preview(
                academic_year=previous_acad,
                from_term=previous_term,
                to_term=to_term,
                to_academic_year=to_year
            )
            summary = preview.get('summary') or {}
            warnings = preview.get('warnings') or []
            self.preview_students_var.set(str(summary.get('total_students', 0)))
            self.preview_reset_var.set(str(summary.get('reset_students', 0)))
            self.preview_carry_var.set(str(summary.get('carry_students', 0)))
            self.preview_previous_total_var.set(format_currency(float(summary.get('previous_outstanding_total', 0) or 0)))
            self.preview_opening_total_var.set(format_currency(float(summary.get('opening_balance_total', 0) or 0)))
            preview_message = (
                f"Preview ready. {summary.get('carry_students', 0)} students will carry balances forward, "
                f"{summary.get('credit_students', 0)} will carry a credit "
                f"({format_currency(float(summary.get('credit_carried_total', 0) or 0))}) "
                f"and {summary.get('reset_students', 0)} will reset."
            )
            if year_changes:
                preview_message += (
                    f"\n\nThis starts academic year {to_year}. Last year's dates have been cleared above; "
                    f"enter the new year's term dates."
                )
            if warnings:
                preview_message = f"{preview_message}\n\nWarning: {' '.join(warnings)}"
            self.preview_message_var.set(preview_message)
            self._pending_rollover_preview = preview
        except Exception as e:
            self.preview_message_var.set(f"Preview unavailable: {e}")
            self._pending_rollover_preview = None
    
    def on_ok(self):
        """Save preferences"""
        previous_acad = getattr(config.Config, 'CURRENT_ACADEMIC_YEAR', None)
        previous_term = getattr(config.Config, 'CURRENT_TERM', None)
        rollover_result = None
        db_settings_before = dict(config.Config.DB_CONFIG)
        try:
            require_login = bool(self.require_login_var.get())
            if require_login and not any(
                    isinstance(info, dict) and info.get('role') == 'Administrator' and info.get('password')
                    for info in (config.Config.USERS or {}).values()):
                raise ValueError("Before turning on the password requirement, create an Administrator "
                                 "with a password under Edit > Manage Users. Otherwise nobody could open "
                                 "the program.")
            schedule = self._validate_academic_configuration()
            acad_input = self.acad_var.get().strip() or previous_acad
            current_term = (self.current_term_var.get() or '').strip() or previous_term
            if not current_term:
                raise ValueError("Select the current active term.")

            term_changed = bool(previous_term and previous_acad and current_term != previous_term)
            if term_changed:
                from models.finance import FinancialManager
                # Raises ValueError when skipping a term; after the last term the
                # academic year moves forward.
                new_acad, _ = FinancialManager._resolve_rollover_target(previous_acad, previous_term, current_term)
                if acad_input not in (previous_acad, new_acad):
                    raise ValueError(f"{current_term} after {previous_term} {previous_acad} belongs to "
                                     f"academic year {new_acad}, not {acad_input}.")
            elif previous_term and previous_acad and acad_input != previous_acad:
                raise ValueError(
                    "The academic year cannot be changed on its own. It moves forward automatically "
                    f"when the active term rolls over from {config.Config.TERMS[-1]} to {config.Config.TERMS[0]}."
                )
            else:
                new_acad = acad_input
            year_changed = bool(previous_acad and new_acad != previous_acad)

            acad_start = self.acad_start_var.get().strip() or None
            acad_end = self.acad_end_var.get().strip() or None
            if year_changed:
                # Dates of the closing year must not filter the new year's figures.
                cutoff = config.Config.academic_year_date_cutoff()
                schedule = config.Config.clear_stale_term_dates(schedule, cutoff)
                acad_start, acad_end = (
                    None if (cutoff and config.Config.parse_config_date(d) and config.Config.parse_config_date(d) <= cutoff) else d
                    for d in (acad_start, acad_end)
                )

            term_start = schedule.get(current_term, {}).get('start_date')
            term_end = schedule.get(current_term, {}).get('end_date')
            if not year_changed:
                term_start = term_start or (self.term_start_var.get().strip() or None)
                term_end = term_end or (self.term_end_var.get().strip() or None)

            if term_changed:
                preview = getattr(self, '_pending_rollover_preview', None)
                if (not preview or preview.get('to_term') != current_term or preview.get('from_term') != previous_term
                        or preview.get('to_academic_year') != new_acad):
                    preview = FinancialManager.get_term_rollover_preview(
                        academic_year=previous_acad,
                        from_term=previous_term,
                        to_term=current_term,
                        to_academic_year=new_acad
                    )
                summary = preview.get('summary') or {}
                carry_students = int(summary.get('carry_students', 0) or 0)
                reset_students = int(summary.get('reset_students', 0) or 0)
                credit_students = int(summary.get('credit_students', 0) or 0)
                warning_line = (
                    "\n\nWarning: Some students still have unpaid balances that will be carried forward."
                    if carry_students > 0 else ""
                )
                year_line = (
                    f"\n\nThis closes academic year {previous_acad} and opens {new_acad}."
                    if year_changed else ""
                )
                confirmed = messagebox.askyesno(
                    "Confirm Term Change",
                    f"Change the active term from {previous_term} {previous_acad} to {current_term} {new_acad}?\n\n"
                    f"Students reviewed: {summary.get('total_students', 0)}\n"
                    f"Balances resetting: {reset_students}\n"
                    f"Balances carried forward: {carry_students}\n"
                    f"Credits carried forward: {credit_students} "
                    f"({format_currency(float(summary.get('credit_carried_total', 0) or 0))})\n"
                    f"Previous outstanding total: {format_currency(float(summary.get('previous_outstanding_total', 0) or 0))}\n"
                    f"Opening balance total: {format_currency(float(summary.get('opening_balance_total', 0) or 0))}"
                    f"{warning_line}{year_line}\n\n"
                    f"This will preserve historical records and apply the centralized rollover workflow."
                )
                if not confirmed:
                    return

                rollover_result = FinancialManager.execute_term_rollover(
                    academic_year=previous_acad,
                    from_term=previous_term,
                    to_term=current_term,
                    to_academic_year=new_acad,
                    term_start_date=term_start
                )

            if self.host_var is not None:   # MySQL storage only
                config.Config.DB_CONFIG['host'] = self.host_var.get()
                config.Config.DB_CONFIG['user'] = self.user_var.get()
                config.Config.DB_CONFIG['password'] = self.pass_var.get()
                config.Config.DB_CONFIG['database'] = self.db_var.get()
            config.Config.UI['theme'] = self.theme_var.get()
            config.Config.REQUIRE_LOGIN = require_login   # applied at the next start

            if new_acad:
                if previous_acad and new_acad != previous_acad:
                    config.Config.PREVIOUS_ACADEMIC_YEAR = previous_acad
                config.Config.CURRENT_ACADEMIC_YEAR = new_acad
            config.Config.ACADEMIC_YEAR_START_DATE = acad_start
            config.Config.ACADEMIC_YEAR_END_DATE = acad_end
            config.Config.TERM_SCHEDULE = schedule
            config.Config.TERM_START_DATE = term_start
            config.Config.TERM_END_DATE = term_end
            config.Config.CURRENT_TERM = current_term
            if term_changed:
                config.Config.PREVIOUS_TERM = previous_term

            settings_saved = config.Config.save_user_settings()

            if dict(config.Config.DB_CONFIG) != db_settings_before:
                # The pool holds connections opened with the old credentials.
                from database.connection import db
                db.reset_pool()

            if not settings_saved:
                messagebox.showwarning(
                    "Settings Not Persisted",
                    "Changes are active for this session but could not be written to the "
                    "settings file. They will be lost when the application restarts."
                    + ("\n\nThe term rollover itself WAS committed to the database."
                       if rollover_result else "")
                )

            try:
                root = self.dialog.nametowidget('.')  # main window, where app events are bound
                root.event_generate('<<PreferencesChanged>>')
            except Exception:
                pass

            if rollover_result:
                summary = rollover_result.get('summary') or {}
                cloned_fee_types = int(rollover_result.get('cloned_fee_types', 0) or 0)
                messagebox.showinfo(
                    "Term Updated",
                    f"Current term changed to {current_term}.\n\n"
                    f"Balances carried forward: {summary.get('carry_students', 0)}\n"
                    f"Balances reset: {summary.get('reset_students', 0)}\n"
                    f"Opening balance total: {format_currency(float(summary.get('opening_balance_total', 0) or 0))}"
                    + (f"\nFee types copied from the previous term: {cloned_fee_types}" if cloned_fee_types > 0 else "")
                )
            else:
                messagebox.showinfo("Success", "Preferences saved successfully.")

            self.result = True
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            committed_note = (
                "The term rollover WAS committed to the database; review the term settings."
                if rollover_result else "No term change was committed."
            )
            messagebox.showerror(
                "Save Failed",
                f"Preferences could not be saved safely.\n\n{committed_note}\n\nDetails: {e}"
            )


class ChangePasswordDialog(BaseDialog):
    """Dialog for changing the current user's password"""
    def __init__(self, parent, username: str):
        super().__init__(parent, 'Change Password', 420, 240)
        self.username = username
        self.setup_ui()

    def setup_ui(self):
        frame = self.main_frame
        ttk.Label(frame, text=f'Change password for: {self.username}').pack(anchor='w', pady=(0,8))

        ttk.Label(frame, text='Current Password:').pack(anchor='w')
        self.current_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.current_var, show='*').pack(fill='x', pady=(0,8))

        ttk.Label(frame, text='New Password:').pack(anchor='w')
        self.new_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.new_var, show='*').pack(fill='x', pady=(0,8))

        ttk.Label(frame, text='Confirm New Password:').pack(anchor='w')
        self.confirm_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.confirm_var, show='*').pack(fill='x', pady=(0,8))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=(8,0))
        ttk.Button(btn_frame, text='Change', command=self.on_ok).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Cancel', command=self.on_cancel).pack(side='left')

    def on_ok(self):
        current = self.current_var.get() or ''
        new = self.new_var.get() or ''
        confirm = self.confirm_var.get() or ''

        if not new:
            messagebox.showerror('Validation', 'New password cannot be empty')
            return
        if new != confirm:
            messagebox.showerror('Validation', 'New passwords do not match')
            return

        info = config.Config.get_user_info(self.username) or {}
        if info.get('password'):
            if not config.Config.verify_user_credentials(self.username, current):
                messagebox.showerror('Authentication', 'Current password is incorrect')
                return

        if config.Config.set_user_password(self.username, new):
            messagebox.showinfo('Success', 'Password changed successfully')
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror('Error', 'Failed to change password')
    
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
        info_text += "© 2025 School Administration\n"
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


class AuditLogViewer(BaseDialog):
    """Dialog for viewing system audit logs"""
    
    def __init__(self, parent):
        from utils.audit_logger import AuditLogger
        
        self.audit_logger = AuditLogger()
        super().__init__(parent, "Audit Log Viewer", width=1000, height=600)
        self.create_widgets()
    
    def create_widgets(self):
        """Create audit log viewer widgets"""
        # Search frame
        search_frame = ttk.LabelFrame(self.main_frame, text="Search & Filter", padding="10")
        search_frame.pack(fill='x', pady=(0, 10))
        
        # Search fields
        ttk.Label(search_frame, text="User:").grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.user_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.user_var, width=15).grid(row=0, column=1, sticky='w', padx=(0, 15))
        
        ttk.Label(search_frame, text="Action:").grid(row=0, column=2, sticky='w', padx=(0, 5))
        self.action_var = tk.StringVar()
        action_combo = ttk.Combobox(search_frame, textvariable=self.action_var, width=15, state='readonly')
        actions = ['ALL', 'LOGIN', 'LOGOUT', 'CREATE', 'UPDATE', 'DELETE', 'VIEW', 'PAYMENT', 'ATTENDANCE']
        action_combo['values'] = actions
        action_combo.set('ALL')
        action_combo.grid(row=0, column=3, sticky='w', padx=(0, 15))
        
        ttk.Label(search_frame, text="Date Range:").grid(row=0, column=4, sticky='w', padx=(0, 5))
        self.days_var = tk.StringVar(value="7")
        days_spin = ttk.Spinbox(search_frame, from_=1, to=365, textvariable=self.days_var, width=8)
        days_spin.grid(row=0, column=5, sticky='w', padx=(0, 5))
        ttk.Label(search_frame, text="days").grid(row=0, column=6, sticky='w', padx=(0, 15))
        
        # Search button
        ttk.Button(search_frame, text="Search", command=self.search_logs).grid(row=0, column=7, padx=(5, 0))
        
        # Results frame with treeview
        results_frame = ttk.LabelFrame(self.main_frame, text="Audit Logs", padding="5")
        results_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Create scrollbars
        vsb = ttk.Scrollbar(results_frame, orient='vertical')
        hsb = ttk.Scrollbar(results_frame, orient='horizontal')
        
        # Create treeview
        columns = ('Timestamp', 'User', 'Action', 'Entity', 'Status')
        self.tree = ttk.Treeview(
            results_frame,
            columns=columns,
            height=20,
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Define headings
        self.tree.heading('#0', text='ID')
        self.tree.column('#0', width=50)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        
        # Details frame
        details_frame = ttk.LabelFrame(self.main_frame, text="Details", padding="5")
        details_frame.pack(fill='x', pady=(0, 10))
        
        self.details_text = tk.Text(details_frame, height=4, width=80, state='disabled')
        self.details_text.pack(fill='both', expand=True)
        
        # Bind selection
        self.tree.bind('<<TreeviewSelect>>', self.on_select_log)
        
        # Button frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill='x')
        
        ttk.Button(button_frame, text="Export to CSV", command=self.export_logs).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Clear Logs", command=self.clear_logs).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Close", command=self.on_cancel).pack(side='right')
        
        # Load initial data
        self.search_logs()
    
    def search_logs(self):
        """Search and filter audit logs"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            user = self.user_var.get().strip() if self.user_var.get().strip() else None
            action = self.action_var.get() if self.action_var.get() != 'ALL' else None
            days = int(self.days_var.get())
            
            # Get logs from database
            logs = self.audit_logger.get_user_actions(user, limit=1000)
            
            # Filter by action if specified
            if action:
                logs = [l for l in logs if l.get('action') == action]
            
            # Filter by date range
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_logs = []
            
            for log in logs:
                try:
                    log_date = datetime.fromisoformat(log.get('timestamp', ''))
                    if log_date >= cutoff_date:
                        filtered_logs.append(log)
                except:
                    filtered_logs.append(log)
            
            # Populate treeview
            for idx, log in enumerate(filtered_logs):
                timestamp = log.get('timestamp', 'N/A')[:19]  # Truncate to date time
                user = log.get('user', 'System')
                action = log.get('action', 'UNKNOWN')
                entity = f"{log.get('entity_type', 'N/A')}#{log.get('entity_id', 'N/A')}"
                status = log.get('status', 'UNKNOWN')
                
                self.tree.insert('', 'end', text=str(log.get('log_id', idx)), 
                               values=(timestamp, user, action, entity, status),
                               tags=('data',))
            
            messagebox.showinfo('Search Complete', f'Found {len(filtered_logs)} audit log entries')
        
        except Exception as e:
            messagebox.showerror('Error', f'Failed to search logs: {str(e)}')
    
    def on_select_log(self, event):
        """Display selected log details"""
        selection = self.tree.selection()
        if not selection:
            return
        
        try:
            item = selection[0]
            values = self.tree.item(item)['values']
            
            # Display details
            details = f"""
Timestamp: {values[0]}
User: {values[1]}
Action: {values[2]}
Entity: {values[3]}
Status: {values[4]}
            """
            
            self.details_text.config(state='normal')
            self.details_text.delete(1.0, 'end')
            self.details_text.insert(1.0, details)
            self.details_text.config(state='disabled')
        
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load details: {str(e)}')
    
    def export_logs(self):
        """Export logs to CSV"""
        try:
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if not file_path:
                return
            
            # Get all logs
            logs = self.audit_logger.get_user_actions(limit=10000)
            
            # Write to CSV
            import csv
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['log_id', 'timestamp', 'user', 'action', 
                                                        'entity_type', 'entity_id', 'status', 'details'])
                writer.writeheader()
                writer.writerows(logs)
            
            messagebox.showinfo('Success', f'Logs exported to {file_path}')
        
        except Exception as e:
            messagebox.showerror('Error', f'Failed to export logs: {str(e)}')
    
    def clear_logs(self):
        """Clear audit logs with confirmation"""
        if messagebox.askyesno('Confirm', 'Are you sure you want to clear all audit logs?'):
            try:
                # Note: This would require implementing a delete method in audit_logger
                messagebox.showinfo('Info', 'Logs clearing not implemented. Contact admin.')
            except Exception as e:
                messagebox.showerror('Error', f'Failed to clear logs: {str(e)}')
    
    def on_ok(self):
        """Override to just close"""
        self.dialog.destroy()
    
    def on_cancel(self):
        """Close the dialog"""
        self.dialog.destroy()


class EmailConfigurationDialog(BaseDialog):
    """Dialog for configuring email notification settings"""
    
    def __init__(self, parent):
        super().__init__(parent, "Email Configuration", width=600, height=500)
        self.create_widgets()
        self.load_settings()
    
    def create_widgets(self):
        """Create email configuration widgets"""
        # Email Server Settings
        server_frame = ttk.LabelFrame(self.main_frame, text="Email Server Settings", padding="10")
        server_frame.pack(fill='x', pady=(0, 10))
        
        # SMTP Server
        ttk.Label(server_frame, text="SMTP Server:").grid(row=0, column=0, sticky='w', pady=5)
        self.smtp_server_var = tk.StringVar()
        ttk.Entry(server_frame, textvariable=self.smtp_server_var, width=40).grid(row=0, column=1, sticky='ew', padx=5)
        
        # SMTP Port
        ttk.Label(server_frame, text="SMTP Port:").grid(row=1, column=0, sticky='w', pady=5)
        self.smtp_port_var = tk.StringVar(value="587")
        ttk.Spinbox(server_frame, from_=1, to=65535, textvariable=self.smtp_port_var, width=10).grid(row=1, column=1, sticky='w', padx=5)
        
        # Use TLS
        self.use_tls_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(server_frame, text="Use TLS", variable=self.use_tls_var).grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        
        # Sender Email
        ttk.Label(server_frame, text="Sender Email:").grid(row=3, column=0, sticky='w', pady=5)
        self.sender_email_var = tk.StringVar()
        ttk.Entry(server_frame, textvariable=self.sender_email_var, width=40).grid(row=3, column=1, sticky='ew', padx=5)
        
        # Sender Name
        ttk.Label(server_frame, text="Sender Name:").grid(row=4, column=0, sticky='w', pady=5)
        self.sender_name_var = tk.StringVar(value="Hope Academy")
        ttk.Entry(server_frame, textvariable=self.sender_name_var, width=40).grid(row=4, column=1, sticky='ew', padx=5)
        
        # Authentication
        auth_frame = ttk.LabelFrame(self.main_frame, text="Authentication", padding="10")
        auth_frame.pack(fill='x', pady=(0, 10))
        
        # Username
        ttk.Label(auth_frame, text="Username:").grid(row=0, column=0, sticky='w', pady=5)
        self.username_var = tk.StringVar()
        ttk.Entry(auth_frame, textvariable=self.username_var, width=40).grid(row=0, column=1, sticky='ew', padx=5)
        
        # Password
        ttk.Label(auth_frame, text="Password:").grid(row=1, column=0, sticky='w', pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(auth_frame, textvariable=self.password_var, width=40, show='*').grid(row=1, column=1, sticky='ew', padx=5)
        
        # Email Preferences
        prefs_frame = ttk.LabelFrame(self.main_frame, text="Notification Preferences", padding="10")
        prefs_frame.pack(fill='x', pady=(0, 10))
        
        # Enable notifications
        self.enable_notifications_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(prefs_frame, text="Enable Email Notifications", 
                       variable=self.enable_notifications_var).grid(row=0, column=0, columnspan=2, sticky='w', pady=5)
        
        # Payment reminders
        self.payment_reminder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(prefs_frame, text="Send Payment Reminders", 
                       variable=self.payment_reminder_var).grid(row=1, column=0, columnspan=2, sticky='w', pady=5)
        
        # Payment confirmations
        self.payment_confirm_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(prefs_frame, text="Send Payment Confirmations", 
                       variable=self.payment_confirm_var).grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        
        # Attendance alerts
        self.attendance_alert_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(prefs_frame, text="Send Attendance Alerts", 
                       variable=self.attendance_alert_var).grid(row=3, column=0, columnspan=2, sticky='w', pady=5)
        
        # Test Connection Button
        test_frame = ttk.Frame(self.main_frame)
        test_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Button(test_frame, text="Test Connection", 
                  command=self.test_connection).pack(side='left', padx=(0, 5))
        
        self.status_label = ttk.Label(test_frame, text="", foreground="gray")
        self.status_label.pack(side='left', padx=5)
        
        # Button box
        self.create_button_box(self.main_frame)
        
        # Configure grid weights
        server_frame.columnconfigure(1, weight=1)
        auth_frame.columnconfigure(1, weight=1)
    
    def load_settings(self):
        """Load email settings from config"""
        try:
            import config
            if hasattr(config, 'EMAIL_CONFIG'):
                email_cfg = config.EMAIL_CONFIG
                self.smtp_server_var.set(email_cfg.get('smtp_server', 'smtp.gmail.com'))
                self.smtp_port_var.set(str(email_cfg.get('smtp_port', 587)))
                self.use_tls_var.set(email_cfg.get('use_tls', True))
                self.sender_email_var.set(email_cfg.get('sender_email', ''))
                self.sender_name_var.set(email_cfg.get('sender_name', 'Hope Academy'))
                self.username_var.set(email_cfg.get('username', ''))
                self.password_var.set(email_cfg.get('password', ''))
        except:
            pass
    
    def test_connection(self):
        """Test email connection"""
        try:
            from utils.email_notifier import EmailNotifier, EmailConfig
            
            email_config = EmailConfig(
                smtp_server=self.smtp_server_var.get(),
                smtp_port=int(self.smtp_port_var.get()),
                sender_email=self.sender_email_var.get(),
                sender_name=self.sender_name_var.get(),
                username=self.username_var.get(),
                password=self.password_var.get(),
                use_tls=self.use_tls_var.get()
            )
            
            notifier = EmailNotifier(email_config)
            result = notifier.test_connection()
            
            if result:
                self.status_label.config(text="✓ Connection successful!", foreground="green")
                messagebox.showinfo('Success', 'Email connection test passed!')
            else:
                self.status_label.config(text="✗ Connection failed", foreground="red")
                messagebox.showerror('Error', 'Email connection test failed')
        
        except Exception as e:
            self.status_label.config(text="✗ Connection failed", foreground="red")
            messagebox.showerror('Error', f'Connection test error: {str(e)}')
    
    def on_ok(self):
        """Save email configuration"""
        try:
            # Save to config
            import config
            
            config.EMAIL_CONFIG = {
                'smtp_server': self.smtp_server_var.get(),
                'smtp_port': int(self.smtp_port_var.get()),
                'sender_email': self.sender_email_var.get(),
                'sender_name': self.sender_name_var.get(),
                'username': self.username_var.get(),
                'password': self.password_var.get(),
                'use_tls': self.use_tls_var.get(),
                'enable_notifications': self.enable_notifications_var.get(),
                'payment_reminder': self.payment_reminder_var.get(),
                'payment_confirmation': self.payment_confirm_var.get(),
                'attendance_alert': self.attendance_alert_var.get()
            }
            
            # Save to file if needed
            self.save_to_file()
            
            self.result = True
            self.dialog.destroy()
        
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save configuration: {str(e)}')
    
    def save_to_file(self):
        """Save configuration to file"""
        try:
            import json
            import os
            
            config_file = 'data/email_config.json'
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            config_data = {
                'smtp_server': self.smtp_server_var.get(),
                'smtp_port': int(self.smtp_port_var.get()),
                'sender_email': self.sender_email_var.get(),
                'sender_name': self.sender_name_var.get(),
                'username': self.username_var.get(),
                'password': self.password_var.get(),
                'use_tls': self.use_tls_var.get()
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except:
            pass
