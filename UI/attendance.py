"""
Attendance Tab - UI for managing student attendance
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date, timedelta
import config
from models.student import Student
from models.attendance import Attendance, AttendanceManager
from UI.dialogs import AttendanceDialog, ConfirmationDialog

class AttendanceTab:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        self.selected_date = date.today()
        self.current_class = "All"
        self.setup_ui()
        self.load_attendance()
    
    def setup_ui(self):
        """Setup attendance tab UI"""
        # Main container
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title_label = ttk.Label(
            main_container, 
            text="Attendance Management",
            style='Title.TLabel'
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Control frame (date and class selection)
        control_frame = ttk.Frame(main_container)
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Date selection
        date_frame = ttk.Frame(control_frame)
        date_frame.pack(side='left', fill='x', expand=True)
        
        ttk.Label(date_frame, text="Date:").pack(side='left', padx=(0, 5))
        
        # Date navigation buttons
        prev_day_btn = ttk.Button(
            date_frame,
            text="◀",
            width=3,
            command=self.previous_day
        )
        prev_day_btn.pack(side='left', padx=(0, 5))
        
        self.date_label = ttk.Label(
            date_frame,
            text=self.selected_date.strftime("%A, %B %d, %Y"),
            font=('Arial', 10, 'bold'),
            width=25
        )
        self.date_label.pack(side='left', padx=5)
        
        next_day_btn = ttk.Button(
            date_frame,
            text="▶",
            width=3,
            command=self.next_day
        )
        next_day_btn.pack(side='left', padx=(0, 10))
        
        # Today button
        today_btn = ttk.Button(
            date_frame,
            text="Today",
            command=self.go_to_today,
            width=8
        )
        today_btn.pack(side='left')
        
        # Class selection
        class_frame = ttk.Frame(control_frame)
        class_frame.pack(side='right')
        
        ttk.Label(class_frame, text="Class:").pack(side='left', padx=(0, 5))
        self.class_var = tk.StringVar(value="All")
        self.class_combo = ttk.Combobox(
            class_frame,
            textvariable=self.class_var,
            values=self.get_class_list(),
            width=15,
            state='readonly'
        )
        self.class_combo.pack(side='left', padx=(0, 5))
        self.class_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_by_class())
        
        # Action buttons frame
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill='x', pady=(0, 10))
        
        # Left side buttons
        left_frame = ttk.Frame(action_frame)
        left_frame.pack(side='left')
        
        self.mark_all_btn = ttk.Button(
            left_frame,
            text="Mark All Present",
            command=self.mark_all_present,
            style='Success.TButton',
            state='disabled'
        )
        self.mark_all_btn.pack(side='left', padx=(0, 5))
        
        self.mark_all_absent_btn = ttk.Button(
            left_frame,
            text="Mark All Absent",
            command=self.mark_all_absent,
            style='Danger.TButton',
            state='disabled'
        )
        self.mark_all_absent_btn.pack(side='left', padx=5)
        
        self.save_btn = ttk.Button(
            left_frame,
            text="Save Attendance",
            command=self.save_attendance,
            style='Primary.TButton'
        )
        self.save_btn.pack(side='left', padx=5)
        
        # Right side buttons
        right_frame = ttk.Frame(action_frame)
        right_frame.pack(side='right')
        
        self.view_report_btn = ttk.Button(
            right_frame,
            text="View Report",
            command=self.view_report
        )
        self.view_report_btn.pack(side='left', padx=(0, 5))
        
        refresh_btn = ttk.Button(
            right_frame,
            text="Refresh",
            command=self.load_attendance
        )
        refresh_btn.pack(side='left')
        
        # Create attendance treeview
        tree_frame = ttk.Frame(main_container)
        tree_frame.pack(fill='both', expand=True)
        
        # Define columns
        columns = ('ID', 'Code', 'Name', 'Class', 'Status', 'Check In', 'Check Out', 'Remarks')
        
        # Create treeview
        self.attendance_tree = ttk.Treeview(
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
            'Status': 100,
            'Check In': 80,
            'Check Out': 80,
            'Remarks': 150
        }
        
        for col in columns:
            self.attendance_tree.heading(col, text=col)
            self.attendance_tree.column(col, width=column_widths.get(col, 100))
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.attendance_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.attendance_tree.xview)
        self.attendance_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.attendance_tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Bind double-click to edit attendance
        self.attendance_tree.bind('<Double-1>', lambda e: self.edit_attendance())
        
        # Status frame (bottom)
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill='x', pady=(10, 0))
        
        # Statistics
        self.stats_label = ttk.Label(status_frame, text="")
        self.stats_label.pack(side='left')
        
        # Last saved
        self.last_saved_label = ttk.Label(status_frame, text="", foreground='gray')
        self.last_saved_label.pack(side='right')
    
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
    
    def load_attendance(self):
        """Load attendance for selected date"""
        # Clear existing items
        for item in self.attendance_tree.get_children():
            self.attendance_tree.delete(item)
        
        # Update date label
        self.date_label.config(text=self.selected_date.strftime("%A, %B %d, %Y"))
        
        try:
            # Get attendance for the date
            attendance_records = Attendance.get_by_date(self.selected_date)
            attendance_dict = {str(r.student_id): r for r in attendance_records}
            
            # Get students (filter by class if needed)
            if self.current_class == "All":
                students = Student.get_all()
            else:
                students = Student.get_by_class(self.current_class)
            
            # Insert into treeview
            present_count = 0
            absent_count = 0
            late_count = 0
            excused_count = 0
            
            for student in students:
                # Get attendance record if exists
                record = attendance_dict.get(str(student.student_id))
                
                if record:
                    status = record.status
                    check_in = record.check_in_time.strftime('%H:%M') if record.check_in_time else ''
                    check_out = record.check_out_time.strftime('%H:%M') if record.check_out_time else ''
                    remarks = record.remarks or ''
                else:
                    status = "Present"  # Default
                    check_in = ''
                    check_out = ''
                    remarks = ''
                
                # Count statuses
                if status == "Present":
                    present_count += 1
                elif status == "Absent":
                    absent_count += 1
                elif status == "Late":
                    late_count += 1
                elif status == "Excused":
                    excused_count += 1
                
                # Color tags based on status
                tags = (status.lower(),)
                
                self.attendance_tree.insert('', 'end', values=(
                    student.student_id,
                    student.student_code,
                    f"{student.first_name} {student.last_name}",
                    student.class_name,
                    status,
                    check_in,
                    check_out,
                    remarks
                ), tags=tags)
            
            # Configure tag colors
            self.attendance_tree.tag_configure('present', foreground='green')
            self.attendance_tree.tag_configure('absent', foreground='red')
            self.attendance_tree.tag_configure('late', foreground='orange')
            self.attendance_tree.tag_configure('excused', foreground='blue')
            
            # Update statistics
            total = len(students)
            if total > 0:
                attendance_rate = (present_count / total) * 100
                stats_text = (f"Total: {total} | Present: {present_count} | Absent: {absent_count} | "
                             f"Late: {late_count} | Excused: {excused_count} | "
                             f"Rate: {attendance_rate:.1f}%")
            else:
                stats_text = "No students found"
            
            self.stats_label.config(text=stats_text)
            
            # Update button states
            has_students = total > 0
            self.mark_all_btn.state(['!disabled'] if has_students else ['disabled'])
            self.mark_all_absent_btn.state(['!disabled'] if has_students else ['disabled'])
            self.save_btn.state(['!disabled'] if has_students else ['disabled'])
            
            # Update last saved
            if attendance_records:
                self.last_saved_label.config(text=f"Last saved: {self.selected_date}")
            else:
                self.last_saved_label.config(text="Not saved yet")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load attendance: {str(e)}")
            self.stats_label.config(text="Error loading attendance")
    
    def filter_by_class(self):
        """Filter attendance by selected class"""
        self.current_class = self.class_var.get()
        self.load_attendance()
    
    def previous_day(self):
        """Go to previous day"""
        self.selected_date -= timedelta(days=1)
        self.load_attendance()
    
    def next_day(self):
        """Go to next day"""
        self.selected_date += timedelta(days=1)
        self.load_attendance()
    
    def go_to_today(self):
        """Go to today's date"""
        self.selected_date = date.today()
        self.load_attendance()
    
    def edit_attendance(self):
        """Edit attendance for selected student"""
        selected = self.attendance_tree.selection()
        
        if not selected:
            return
        
        item = selected[0]
        values = self.attendance_tree.item(item, 'values')
        student_id = values[0]
        student_name = values[2]
        
        # Get current attendance record
        try:
            # Check if attendance already exists for this date
            from database.connection import db
            query = """
                SELECT * FROM attendance 
                WHERE student_id = %s AND attendance_date = %s
            """
            result = db.execute_query(query, (student_id, self.selected_date), fetch=True)
            
            attendance_data = None
            if result:
                attendance_data = {
                    'status': result[0]['status'],
                    'check_in_time': result[0]['check_in_time'],
                    'check_out_time': result[0]['check_out_time'],
                    'remarks': result[0]['remarks']
                }
            
            # Show attendance dialog
            dialog = AttendanceDialog(
                self.frame,
                title=f"Edit Attendance - {student_name}",
                date=self.selected_date,
                student_id=student_id,
                attendance_data=attendance_data
            )
            
            if dialog.show():
                # Update treeview with new values
                new_status = dialog.status_var.get()
                check_in = dialog.check_in_var.get()
                check_out = dialog.check_out_var.get()
                remarks = dialog.remarks_entry.get("1.0", tk.END).strip()
                
                self.attendance_tree.item(item, values=(
                    values[0], values[1], values[2], values[3],
                    new_status, check_in, check_out, remarks
                ), tags=(new_status.lower(),))
                
                # Update statistics
                self.update_statistics()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit attendance: {str(e)}")
    
    def mark_all_present(self):
        """Mark all students as present"""
        response = messagebox.askyesno(
            "Mark All Present",
            "Mark all students as Present?\n\n"
            "This will override existing statuses."
        )
        
        if not response:
            return
        
        # Update all items in treeview
        for item in self.attendance_tree.get_children():
            values = list(self.attendance_tree.item(item, 'values'))
            values[4] = "Present"  # Status column
            values[5] = "08:00" if not values[5] else values[5]  # Default check-in
            self.attendance_tree.item(item, values=tuple(values), tags=('present',))
        
        # Update statistics
        self.update_statistics()
    
    def mark_all_absent(self):
        """Mark all students as absent"""
        response = messagebox.askyesno(
            "Mark All Absent",
            "Mark all students as Absent?\n\n"
            "This will override existing statuses."
        )
        
        if not response:
            return
        
        # Update all items in treeview
        for item in self.attendance_tree.get_children():
            values = list(self.attendance_tree.item(item, 'values'))
            values[4] = "Absent"  # Status column
            values[5] = ""  # Clear check-in
            values[6] = ""  # Clear check-out
            values[7] = ""  # Clear remarks
            self.attendance_tree.item(item, values=tuple(values), tags=('absent',))
        
        # Update statistics
        self.update_statistics()
    
    def update_statistics(self):
        """Update attendance statistics"""
        present_count = 0
        absent_count = 0
        late_count = 0
        excused_count = 0
        
        for item in self.attendance_tree.get_children():
            values = self.attendance_tree.item(item, 'values')
            status = values[4]
            
            if status == "Present":
                present_count += 1
            elif status == "Absent":
                absent_count += 1
            elif status == "Late":
                late_count += 1
            elif status == "Excused":
                excused_count += 1
        
        total = len(self.attendance_tree.get_children())
        if total > 0:
            attendance_rate = (present_count / total) * 100
            stats_text = (f"Total: {total} | Present: {present_count} | Absent: {absent_count} | "
                         f"Late: {late_count} | Excused: {excused_count} | "
                         f"Rate: {attendance_rate:.1f}%")
        else:
            stats_text = "No students"
        
        self.stats_label.config(text=stats_text)
    
    def save_attendance(self):
        """Save attendance records to database"""
        # Collect attendance data from treeview
        attendance_data = []
        
        for item in self.attendance_tree.get_children():
            values = self.attendance_tree.item(item, 'values')
            
            student_id = values[0]
            status = values[4]
            check_in = values[5] if values[5] else None
            check_out = values[6] if values[6] else None
            remarks = values[7] if values[7] else ''
            
            # Parse times
            from datetime import time as dt_time
            check_in_time = None
            check_out_time = None
            
            if check_in:
                try:
                    hour, minute = map(int, check_in.split(':'))
                    check_in_time = dt_time(hour, minute)
                except:
                    pass
            
            if check_out:
                try:
                    hour, minute = map(int, check_out.split(':'))
                    check_out_time = dt_time(hour, minute)
                except:
                    pass
            
            attendance_data.append({
                'student_id': student_id,
                'status': status,
                'check_in_time': check_in_time,
                'check_out_time': check_out_time,
                'remarks': remarks
            })
        
        if not attendance_data:
            messagebox.showwarning("No Data", "No attendance data to save")
            return
        
        # Confirm save
        response = messagebox.askyesno(
            "Save Attendance",
            f"Save attendance for {self.selected_date}?\n\n"
            f"Total records: {len(attendance_data)}"
        )
        
        if not response:
            return
        
        try:
            # Save attendance records
            success_count = 0
            error_messages = []
            
            for record in attendance_data:
                attendance = Attendance(
                    student_id=record['student_id'],
                    attendance_date=self.selected_date,
                    status=record['status'],
                    check_in_time=record['check_in_time'],
                    check_out_time=record['check_out_time'],
                    remarks=record['remarks'],
                    recorded_by="System"  # In real app, would be current user
                )
                
                success, message = attendance.save()
                if success:
                    success_count += 1
                else:
                    error_messages.append(f"Student ID {record['student_id']}: {message}")
            
            # Show result
            if error_messages:
                error_count = len(error_messages)
                if success_count > 0:
                    message = f"Saved {success_count} records. {error_count} errors occurred."
                    if error_count <= 3:
                        message += f"\n\nErrors:\n" + "\n".join(error_messages[:3])
                    messagebox.showwarning("Partial Success", message)
                else:
                    messagebox.showerror("Error", "Failed to save attendance:\n" + "\n".join(error_messages[:5]))
            else:
                messagebox.showinfo("Success", f"Attendance saved successfully for {success_count} students")
                self.last_saved_label.config(text=f"Last saved: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save attendance: {str(e)}")
    
    def view_report(self):
        """View attendance report"""
        from datetime import datetime
        from tkinter import simpledialog
        
        # Ask for date range
        start_date_str = simpledialog.askstring(
            "Start Date",
            "Enter start date (YYYY-MM-DD):",
            initialvalue=(date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
        )
        
        if not start_date_str:
            return
        
        end_date_str = simpledialog.askstring(
            "End Date",
            "Enter end date (YYYY-MM-DD):",
            initialvalue=date.today().strftime('%Y-%m-%d')
        )
        
        if not end_date_str:
            return
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if start_date > end_date:
                messagebox.showerror("Error", "Start date cannot be after end date")
                return
            
            # Generate report
            report = AttendanceManager.get_daily_attendance_report(start_date)
            
            if not report:
                messagebox.showinfo("No Data", f"No attendance data found for {start_date}")
                return
            
            # Show report in a new window
            report_window = tk.Toplevel(self.frame)
            report_window.title(f"Attendance Report - {start_date_str} to {end_date_str}")
            report_window.geometry("800x600")
            
            # Create text widget for report
            text_widget = tk.Text(report_window, wrap='word')
            text_widget.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(text_widget)
            scrollbar.pack(side='right', fill='y')
            text_widget.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=text_widget.yview)
            
            # Format report
            report_text = f"ATTENDANCE REPORT\n"
            report_text += "=" * 50 + "\n\n"
            report_text += f"Period: {start_date_str} to {end_date_str}\n"
            report_text += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report_text += "\n" + "=" * 50 + "\n\n"
            
            report_text += f"Total Students: {report['total_students']}\n"
            report_text += f"Present: {report['present']}\n"
            report_text += f"Absent: {report['absent']}\n"
            report_text += f"Late: {report['late']}\n"
            report_text += f"Excused: {report['excused']}\n"
            report_text += f"Attendance Rate: {report['attendance_rate']}%\n"
            
            report_text += "\n" + "=" * 50 + "\n\n"
            report_text += "BY CLASS:\n"
            
            for class_name, stats in report.get('class_summary', {}).items():
                total = stats['total']
                present = stats['present']
                rate = (present / total * 100) if total > 0 else 0
                report_text += f"\n{class_name}:\n"
                report_text += f"  Total: {total}, Present: {present} ({rate:.1f}%)\n"
            
            # Insert report text
            text_widget.insert('1.0', report_text)
            text_widget.config(state='disabled')
            
            # Add print button
            print_btn = ttk.Button(
                report_window,
                text="Print Report",
                command=lambda: self.print_report(report_text)
            )
            print_btn.pack(pady=10)
            
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
    
    def print_report(self, report_text):
        """Print attendance report"""
        try:
            from tkinter import filedialog
            
            # Ask for file location
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"attendance_report_{date.today()}.txt"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write(report_text)
                
                messagebox.showinfo("Success", f"Report saved to:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {str(e)}")
    
    def refresh_data(self):
        """Public method to refresh data (called from main window)"""
        self.load_attendance()
        self.class_combo['values'] = self.get_class_list()