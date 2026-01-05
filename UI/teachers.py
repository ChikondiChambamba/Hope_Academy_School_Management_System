"""
Teachers Tab - UI for managing teachers
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import config
from models.teacher import Teacher, TeacherManager
from UI.dialogs import TeacherDialog, ConfirmationDialog

class TeachersTab:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.setup_ui()
        self.load_teachers()
    
    def setup_ui(self):
        """Setup teachers tab UI"""
        # Main container with padding
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(
            main_container, 
            text="Teacher Management",
            style='Title.TLabel'
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Control buttons frame
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill='x', pady=(0, 10))
        
        # Buttons
        self.add_button = ttk.Button(
            controls_frame, 
            text="Add Teacher",
            command=self.add_teacher,
            style='Success.TButton'
        )
        self.add_button.pack(side='left', padx=(0, 5))
        
        self.edit_button = ttk.Button(
            controls_frame, 
            text="Edit Teacher",
            command=self.edit_teacher,
            style='Primary.TButton'
        )
        self.edit_button.pack(side='left', padx=5)
        
        self.delete_button = ttk.Button(
            controls_frame, 
            text="Delete Teacher",
            command=self.delete_teacher,
            style='Danger.TButton'
        )
        self.delete_button.pack(side='left', padx=5)
        
        self.refresh_button = ttk.Button(
            controls_frame, 
            text="Refresh",
            command=self.load_teachers
        )
        self.refresh_button.pack(side='right', padx=(5, 0))
        
        # Search frame
        search_frame = ttk.Frame(controls_frame)
        search_frame.pack(side='right', padx=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        self.search_entry.pack(side='left', padx=(0, 5))
        
        search_button = ttk.Button(
            search_frame,
            text="Go",
            command=self.search_teachers,
            width=5
        )
        search_button.pack(side='left')
        
        # Bind Enter key to search
        self.search_entry.bind('<Return>', lambda e: self.search_teachers())
        
        # Create treeview with scrollbars
        tree_frame = ttk.Frame(main_container)
        tree_frame.pack(fill='both', expand=True)
        
        # Define columns
        columns = ('ID', 'Code', 'First Name', 'Last Name', 'Specialization', 
                  'Phone', 'Email', 'Hire Date', 'Status')
        
        # Create treeview
        self.teachers_tree = ttk.Treeview(
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
            'Specialization': 120,
            'Phone': 100,
            'Email': 150,
            'Hire Date': 90,
            'Status': 80
        }
        
        for col in columns:
            self.teachers_tree.heading(col, text=col)
            self.teachers_tree.column(col, width=column_widths.get(col, 100))
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.teachers_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.teachers_tree.xview)
        self.teachers_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout for tree and scrollbars
        self.teachers_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Bind double-click to edit
        self.teachers_tree.bind('<Double-1>', lambda e: self.edit_teacher())
        
        # Bind selection change
        self.teachers_tree.bind('<<TreeviewSelect>>', self.on_selection_change)
        
        # Status label
        self.status_label = ttk.Label(main_container, text="")
        self.status_label.pack(anchor='w', pady=(10, 0))
    
    def load_teachers(self):
        """Load teachers into treeview"""
        # Clear existing items
        for item in self.teachers_tree.get_children():
            self.teachers_tree.delete(item)
        
        try:
            # Get all teachers
            teachers = Teacher.get_all(active_only=True)
            
            # Insert into treeview
            for teacher in teachers:
                status = "Active" if teacher.is_active else "Inactive"
                
                self.teachers_tree.insert('', 'end', values=(
                    teacher.teacher_id,
                    teacher.teacher_code,
                    teacher.first_name,
                    teacher.last_name,
                    teacher.subject_specialization or '',
                    teacher.phone or '',
                    teacher.email or '',
                    teacher.hire_date.strftime('%Y-%m-%d') if teacher.hire_date else '',
                    status
                ))
            
            # Update status
            count = len(teachers)
            self.status_label.config(text=f"Total Teachers: {count}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load teachers: {str(e)}")
            self.status_label.config(text="Error loading teachers")
    
    def search_teachers(self):
        """Search teachers by name or code"""
        search_term = self.search_var.get().strip()
        
        if not search_term:
            self.load_teachers()
            return
        
        # Clear existing items
        for item in self.teachers_tree.get_children():
            self.teachers_tree.delete(item)
        
        try:
            # Search teachers
            teachers = Teacher.search(search_term)
            
            # Insert results
            for teacher in teachers:
                status = "Active" if teacher.is_active else "Inactive"
                
                self.teachers_tree.insert('', 'end', values=(
                    teacher.teacher_id,
                    teacher.teacher_code,
                    teacher.first_name,
                    teacher.last_name,
                    teacher.subject_specialization or '',
                    teacher.phone or '',
                    teacher.email or '',
                    teacher.hire_date.strftime('%Y-%m-%d') if teacher.hire_date else '',
                    status
                ))
            
            # Update status
            count = len(teachers)
            self.status_label.config(text=f"Found {count} teacher(s) matching '{search_term}'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {str(e)}")
    
    def add_teacher(self):
        """Open dialog to add new teacher"""
        dialog = TeacherDialog(self.frame, title="Add New Teacher")
        dialog.show()
        
        # Refresh if teacher was added
        if dialog.result:
            self.load_teachers()
    
    def edit_teacher(self):
        """Edit selected teacher"""
        selected = self.teachers_tree.selection()
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select a teacher to edit")
            return
        
        item = selected[0]
        values = self.teachers_tree.item(item, 'values')
        teacher_id = values[0]
        
        try:
            teacher = Teacher.get_by_id(teacher_id)
            if not teacher:
                messagebox.showerror("Error", "Teacher not found")
                return
            
            dialog = TeacherDialog(self.frame, title="Edit Teacher", teacher=teacher)
            dialog.show()
            
            # Refresh if teacher was updated
            if dialog.result:
                self.load_teachers()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit teacher: {str(e)}")
    
    def delete_teacher(self):
        """Delete (deactivate) selected teacher"""
        selected = self.teachers_tree.selection()
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select a teacher to delete")
            return
        
        item = selected[0]
        values = self.teachers_tree.item(item, 'values')
        teacher_id = values[0]
        teacher_name = f"{values[2]} {values[3]}"
        
        # Confirm deletion
        dialog = ConfirmationDialog(
            self.frame,
            title="Confirm Delete",
            message=f"Are you sure you want to delete teacher:\n{teacher_name}?",
            warning="This action cannot be undone."
        )
        
        if not dialog.show():
            return
        
        try:
            # Deactivate teacher
            success, message = TeacherManager.delete_teacher(teacher_id)
            
            if success:
                messagebox.showinfo("Success", message)
                self.load_teachers()
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete teacher: {str(e)}")
    
    def on_selection_change(self, event):
        """Handle treeview selection change"""
        selected = self.teachers_tree.selection()
        self.edit_button.state(['!disabled'] if selected else ['disabled'])
        self.delete_button.state(['!disabled'] if selected else ['disabled'])
    
    def refresh_data(self):
        """Public method to refresh data (called from main window)"""
        self.load_teachers()