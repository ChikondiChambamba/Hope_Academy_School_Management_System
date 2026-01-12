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

        term = self.term_var.get().strip() or config.Config.CURRENT_TERM
        is_required = bool(self.req_var.get())

        self.result_data = {
            'fee_name': name,
            'amount': amount,
            'term': term,
            'is_required': is_required
        }
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
        
        # Get fee types
        fee_types = FeeType.get_all()

        # If student is continuing, registration and uniform should not be selectable
        filtered_fee_types = []
        for ft in fee_types:
            name_l = ft.fee_name.lower()
            if not getattr(self.student, 'is_new', True) and ('registration' in name_l or 'uniform' in name_l):
                continue
            filtered_fee_types.append(ft)

        fee_choices = [f"{ft.fee_name} ({format_currency(ft.amount)})" for ft in filtered_fee_types]

        self._fee_type_lookup = {f"{ft.fee_name} ({format_currency(ft.amount)})": ft for ft in filtered_fee_types}

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
                                   values=["Cash", "M-Pesa", "Bank Transfer", "Check", "Other"], width=15)
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
            # Tuition override by class
            if 'tuition' in fname:
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
            # Parse fee type
            fee_type_str = self.fee_type_var.get()
            fee_name = fee_type_str.split(' (')[0]

            # Get fee type ID
            fee_types = FeeType.get_all()
            fee_type = next((ft for ft in fee_types if ft.fee_name == fee_name), None)

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
                    root = self.dialog.winfo_toplevel()
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
        ttk.Button(btn_frame, text='Edit Role', command=self.edit_role).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Remove User', command=self.remove_user).pack(side='left', padx=4)
        ttk.Button(btn_frame, text='Set As Current', command=self.set_current_user).pack(side='left', padx=4)
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
        if config.Config.add_user(uname, role):
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
        if config.Config.set_user_role(uname, role):
            self.load_users()
            # If current user changed role, emit event
            try:
                root = self.dialog.winfo_toplevel()
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
        if messagebox.askyesno('Confirm', f'Remove user {uname}?'):
            if config.Config.remove_user(uname):
                self.load_users()
                messagebox.showinfo('Removed', f'User {uname} removed')
            else:
                messagebox.showerror('Error', 'Failed to remove user')

    def set_current_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('No Selection', 'Select a user to set as current')
            return
        item = sel[0]
        uname = self.tree.item(item, 'values')[0]
        if config.Config.set_current_user(uname):
            try:
                root = self.dialog.winfo_toplevel()
                root.event_generate('<<UserRoleChanged>>')
            except Exception:
                pass
            self.load_users()
            messagebox.showinfo('Success', f'Logged in as {uname}')
        else:
            messagebox.showerror('Error', 'Failed to set current user')


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
        if config.Config.set_current_user(uname):
            try:
                root = self.dialog.winfo_toplevel()
                root.event_generate('<<UserRoleChanged>>')
            except Exception:
                pass
            self.result = True
            self.dialog.destroy()
        else:
            messagebox.showerror('Login Failed', 'Failed to set current user')
        
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

        # Academic year settings
        acad_frame = ttk.LabelFrame(self.main_frame, text="Academic Year", padding="10")
        acad_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(acad_frame, text="Academic Year:").grid(row=0, column=0, sticky='e', padx=(0,10), pady=5)
        self.acad_var = tk.StringVar(value=getattr(config.Config, 'CURRENT_ACADEMIC_YEAR', ''))
        ttk.Entry(acad_frame, textvariable=self.acad_var, width=20).grid(row=0, column=1, sticky='w', pady=5)

        ttk.Label(acad_frame, text="Term End Date (YYYY-MM-DD):").grid(row=1, column=0, sticky='e', padx=(0,10), pady=5)
        self.term_end_var = tk.StringVar(value=getattr(config.Config, 'TERM_END_DATE', '') or '')
        ttk.Entry(acad_frame, textvariable=self.term_end_var, width=20).grid(row=1, column=1, sticky='w', pady=5)

        ttk.Label(acad_frame, text="Term Start Date (YYYY-MM-DD):").grid(row=2, column=0, sticky='e', padx=(0,10), pady=5)
        self.term_start_var = tk.StringVar(value=getattr(config.Config, 'TERM_START_DATE', '') or '')
        ttk.Entry(acad_frame, textvariable=self.term_start_var, width=20).grid(row=2, column=1, sticky='w', pady=5)

        ttk.Label(acad_frame, text="Current Term:").grid(row=3, column=0, sticky='e', padx=(0,10), pady=5)
        self.current_term_var = tk.StringVar(value=getattr(config.Config, 'CURRENT_TERM', '') or '')
        ttk.Combobox(acad_frame, textvariable=self.current_term_var, values=getattr(config.Config, 'TERMS', ['Term 1','Term 2','Term 3']), width=18, state='readonly').grid(row=3, column=1, sticky='w', pady=5)
        
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
        # Academic year and term
        new_acad = self.acad_var.get().strip()
        if new_acad:
            config.Config.CURRENT_ACADEMIC_YEAR = new_acad
        term_end = self.term_end_var.get().strip()
        config.Config.TERM_END_DATE = term_end if term_end else None
        # Term start and current term
        term_start = self.term_start_var.get().strip()
        config.Config.TERM_START_DATE = term_start if term_start else None
        current_term = self.current_term_var.get().strip()
        if current_term:
            config.Config.CURRENT_TERM = current_term
        # Persist user settings
        try:
            config.Config.save_user_settings()
        except Exception:
            pass

        # Notify application that preferences changed (apply immediately)
        try:
            root = self.dialog.winfo_toplevel()
            root.event_generate('<<PreferencesChanged>>')
        except Exception:
            pass
        
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