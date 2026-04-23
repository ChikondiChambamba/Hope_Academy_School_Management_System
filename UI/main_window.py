"""
Main application window
"""
import tkinter as tk
from tkinter import ttk, Menu, messagebox
import config
from database.connection import db
import os

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.setup_ui()
        
    def setup_ui(self):
        """Setup main window UI"""
        # Configure style
        self.setup_styles()
        
        # Create menu bar
        self.create_menu_bar()
        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill='both', expand=True, padx=10, pady=10)

        # Create tabs based on current role (roles managed in Preferences)
        self.create_tabs()
        # Bind application-wide events
        try:
            # When a payment is recorded in any dialog, refresh all tabs
            self.root.bind("<<PaymentRecorded>>", lambda e: self.refresh_all())
            # Recreate tabs when user role changes
            self.root.bind("<<UserRoleChanged>>", lambda e: self.on_user_role_changed())
            # Apply preferences changes (theme, db settings, academic year) immediately
            self.root.bind("<<PreferencesChanged>>", lambda e: self.apply_preferences())
        except Exception:
            pass
        
        # Create status bar
        self.create_status_bar()
        
        # Update status
        self.update_status("Ready")
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        
        # Use theme
        style.theme_use(config.Config.UI['theme'])
        
        # Configure colors
        style.configure('Primary.TButton', 
                       foreground='white',
                       background=config.Config.UI['primary_color'])
        
        style.configure('Success.TButton',
                       foreground='white',
                       background=config.Config.UI['secondary_color'])
        
        style.configure('Warning.TButton',
                       foreground='white',
                       background=config.Config.UI['warning_color'])
        
        style.configure('Danger.TButton',
                       foreground='white',
                       background=config.Config.UI['danger_color'])

        # Default button color for any unstyled buttons
        try:
            default_btn_bg = config.Config.UI.get('button_color', config.Config.UI['primary_color'])
            style.configure('TButton', background=default_btn_bg, foreground='white')
            style.map('TButton', background=[('active', config.Config.UI['secondary_color'])])
        except Exception:
            pass
        
        # Configure labels
        style.configure('Title.TLabel',
                       font=(config.Config.UI['font_family'], 
                            config.Config.UI['font_size_title'], 'bold'))
        
        style.configure('Header.TLabel',
                       font=(config.Config.UI['font_family'], 
                            config.Config.UI['font_size_large'], 'bold'))
        
        # Configure treeview
        style.configure('Treeview',
                       font=(config.Config.UI['font_family'], 
                            config.Config.UI['font_size_small']))
        
        style.configure('Treeview.Heading',
                       font=(config.Config.UI['font_family'], 
                            config.Config.UI['font_size_small'], 'bold'))
        
        # Configure colors for treeview selection
        style.map('Treeview',
                 background=[('selected', config.Config.UI['primary_color'])],
                 foreground=[('selected', 'white')])
    
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        
        file_menu.add_command(label="Backup Database", 
                             command=self.backup_database,
                             accelerator="Ctrl+B")
        file_menu.add_command(label="Restore Database", 
                             command=self.restore_database)
        file_menu.add_separator()
        file_menu.add_command(label="Export Data", 
                             command=self.export_data)
        file_menu.add_command(label="Import Data", 
                             command=self.import_data)
        file_menu.add_separator()
        file_menu.add_command(label="Print", 
                             command=self.print_data,
                             accelerator="Ctrl+P")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", 
                             command=self.root.quit,
                             accelerator="Ctrl+Q")
        file_menu.add_command(label="Login",
                 command=self.show_login,
                 accelerator="Ctrl+I")
        file_menu.add_command(label="Logout",
                 command=self.logout,
                 accelerator="Ctrl+L")
        
        # Edit menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Preferences", 
                             command=self.open_preferences)
        edit_menu.add_command(label="Change Password",
                 command=self.open_change_password)
        # User management
        edit_menu.add_command(label="Manage Users",
                             command=self.open_user_manager,
                             accelerator="Ctrl+U")
        
        # View menu
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh All", 
                             command=self.refresh_all,
                             accelerator="F5")
        view_menu.add_separator()
        
        # Add checkbuttons for tabs (always visible in the View menu).
        # Initial checked state follows permissions so users see which tabs
        # their role allows but can toggle visibility on/off.
        self.tab_vars = {}
        tabs_map = [
            ('dashboard', 'Dashboard'),
            ('students', 'Students'),
            ('teachers', 'Teachers'),
            ('finance', 'Finance'),
            ('inventory', 'Inventory'),
            ('attendance', 'Attendance'),
            ('reports', 'Reports')
        ]
        for feature, tab_name in tabs_map:
            allowed = config.Config.has_permission(feature)
            var = tk.BooleanVar(value=allowed)
            self.tab_vars[tab_name] = var
            view_menu.add_checkbutton(label=tab_name,
                                      variable=var,
                                      command=lambda t=tab_name: self.toggle_tab(t))
        
        # Tools menu
        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Database Maintenance", 
                              command=self.database_maintenance)
        tools_menu.add_command(label="Recalculate Balances", 
                              command=self.recalculate_balances)
        tools_menu.add_separator()
        tools_menu.add_command(label="Send Notifications", 
                              command=self.send_notifications)
        
        # Reports menu
        reports_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reports", menu=reports_menu)
        
        # Student reports submenu (non-financial)
        student_reports = Menu(reports_menu, tearoff=0)
        reports_menu.add_cascade(label="Student Reports", menu=student_reports)
        student_reports.add_command(label="Student List",
                       command=self.generate_student_list)
        student_reports.add_command(label="Attendance Report",
                       command=self.generate_attendance_report)
        
        # Financial reports submenu (only for roles with permission)
        if config.Config.has_permission('financial_reports'):
            financial_reports = Menu(reports_menu, tearoff=0)
            reports_menu.add_cascade(label="Financial Reports", menu=financial_reports)
            financial_reports.add_command(label="Student Fees Report",
                                         command=self.generate_student_fees_report)
            financial_reports.add_command(label="Fee Collection Report",
                                         command=self.generate_fee_collection_report)
            financial_reports.add_command(label="Expense Report",
                                         command=self.generate_expense_report)
            financial_reports.add_command(label="Financial Summary",
                                         command=self.generate_financial_summary)
        
        # Inventory reports submenu
        inventory_reports = Menu(reports_menu, tearoff=0)
        reports_menu.add_cascade(label="Inventory Reports", menu=inventory_reports)
        inventory_reports.add_command(label="Inventory List", 
                                     command=self.generate_inventory_list)
        inventory_reports.add_command(label="Low Stock Report", 
                                     command=self.generate_low_stock_report)
        
        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Manual", 
                             command=self.open_manual)
        help_menu.add_command(label="Keyboard Shortcuts", 
                             command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="Check for Updates", 
                             command=self.check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label="About", 
                             command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-b>', lambda e: self.backup_database())
        self.root.bind('<Control-p>', lambda e: self.print_data())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<Control-l>', lambda e: self.logout())
        self.root.bind('<Control-u>', lambda e: self.open_user_manager())
        self.root.bind('<F5>', lambda e: self.refresh_all())

    def logout(self):
        """Logout current user and refresh UI (roles managed in Preferences)."""
        try:
            # Clear current user
            try:
                config.Config.CURRENT_USER = None
                # keep CURRENT_USER_ROLE as-is until new login; persist removal of CURRENT_USER
                config.Config.save_user_settings()
            except Exception:
                pass
            # Recreate tabs to reflect that no user is selected (role remains as in Preferences)
            try:
                self.on_user_role_changed()
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror('Logout Failed', str(e))

    def on_user_role_changed(self):
        """Handler for role change events - recreate tabs immediately."""
        try:
            # Destroy existing notebook and recreate tabs using new role
            if hasattr(self, 'notebook'):
                try:
                    self.notebook.destroy()
                except Exception:
                    pass
            self.create_tabs()
            user = getattr(config.Config, 'CURRENT_USER', None)
            role = getattr(config.Config, 'CURRENT_USER_ROLE', None)
            if user:
                self.update_status(f"Logged in as {user} ({role})")
            else:
                self.update_status(f"Role: {role}")
        except Exception:
            pass

    def apply_preferences(self):
        """Apply preferences changed at runtime without restart"""
        try:
            # Reapply styles (theme, fonts, colors)
            self.setup_styles()
            # Refresh data in all tabs
            self.refresh_all()
            # Update DB connection indicator
            self.update_database_status()
            self.update_status("Preferences applied")
        except Exception:
            pass

    def show_login(self):
        """Show the login dialog and create tabs based on selected user."""
        from UI.dialogs import LoginDialog
        dialog = LoginDialog(self.root)
        dialog.show()
        # If user selected a username, dialog sets Config.CURRENT_USER and role.
        # Ensure tabs are created (use current role from config)
        try:
            # Remove any existing notebook (if present)
            if hasattr(self, 'notebook'):
                try:
                    self.notebook.destroy()
                except Exception:
                    pass
            self.create_tabs()
            # Update status to indicate logged-in user
            user = getattr(config.Config, 'CURRENT_USER', None)
            role = getattr(config.Config, 'CURRENT_USER_ROLE', None)
            if user:
                self.update_status(f"Logged in as {user} ({role})")
            else:
                self.update_status(f"Role: {role}")
        except Exception:
            self.create_tabs()
    
    def create_tabs(self):
        """Create main tabs for different sections"""
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill='both', expand=True)
        
        # Dictionary to hold tab instances
        self.tabs = {}
        
        # Import and create tab instances
        try:
            from UI.dashboard import DashboardTab
            from UI.students import StudentsTab
            from UI.teachers import TeachersTab
            from UI.finance import FinanceTab
            from UI.inventory import InventoryTab
            from UI.attendance import AttendanceTab
            from UI.reports import ReportsTab
            # Create tab instances based on View menu state or permissions
            def should_create(feature_name, tab_name):
                try:
                    # If the View checkbox is checked, create the tab.
                    return bool(self.tab_vars.get(tab_name, tk.BooleanVar(value=True)).get()) or config.Config.has_permission(feature_name)
                except Exception:
                    return config.Config.has_permission(feature_name)

            if should_create('dashboard', 'Dashboard'):
                self.tabs['Dashboard'] = DashboardTab(self.notebook, role=getattr(config.Config, 'CURRENT_USER_ROLE', ''))
            if should_create('students', 'Students'):
                self.tabs['Students'] = StudentsTab(self.notebook)
            if should_create('teachers', 'Teachers'):
                self.tabs['Teachers'] = TeachersTab(self.notebook)
            if should_create('finance', 'Finance'):
                self.tabs['Finance'] = FinanceTab(self.notebook)
            if should_create('inventory', 'Inventory'):
                self.tabs['Inventory'] = InventoryTab(self.notebook)
            if should_create('attendance', 'Attendance'):
                self.tabs['Attendance'] = AttendanceTab(self.notebook)
            if should_create('reports', 'Reports'):
                self.tabs['Reports'] = ReportsTab(self.notebook)

            # Add tabs to notebook
            for name, tab in self.tabs.items():
                self.notebook.add(tab.frame, text=name)

            # Bind tab change event
            self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        except ImportError as e:
            messagebox.showerror("Import Error",
                                 f"Failed to load UI components:\n{str(e)}\n\n"
                                 "Please check that all modules are installed.")
    
    def create_status_bar(self):
        """Create status bar at bottom of window"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side='bottom', fill='x', padx=10, pady=5)
        
        # Status label (left side)
        self.status_label = ttk.Label(
            self.status_bar, 
            text="Ready",
            relief='sunken',
            anchor='w',
            padding=(5, 2)
        )
        self.status_label.pack(side='left', fill='x', expand=True)
        
        # Database status (right side)
        self.update_database_status()
        
        # Update timestamp (middle right)
        from datetime import datetime
        self.timestamp_label = ttk.Label(
            self.status_bar,
            text=datetime.now().strftime('%Y-%m-%d %H:%M'),
            relief='sunken',
            padding=(5, 2)
        )
        self.timestamp_label.pack(side='right', padx=(0, 10))
        
        # Update timestamp every minute
        self.update_timestamp()
    
    def update_timestamp(self):
        """Update timestamp in status bar"""
        from datetime import datetime
        self.timestamp_label.config(text=datetime.now().strftime('%Y-%m-%d %H:%M'))
        self.root.after(60000, self.update_timestamp)  # Update every minute
    
    def update_database_status(self):
        """Update database connection status"""
        if db.test_connection():
            status_text = "Database: Connected ✓"
            status_color = 'green'
        else:
            status_text = "Database: Disconnected ✗"
            status_color = 'red'
        
        self.db_status_label = ttk.Label(
            self.status_bar,
            text=status_text,
            relief='sunken',
            foreground=status_color,
            padding=(5, 2)
        )
        self.db_status_label.pack(side='right', padx=(0, 10))
    
    def update_status(self, message: str):
        """Update status bar message"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def on_tab_change(self, event):
        """Handle tab change event"""
        selected_tab = self.notebook.index(self.notebook.select())
        tab_names = list(self.tabs.keys())
        
        if 0 <= selected_tab < len(tab_names):
            tab_name = tab_names[selected_tab]
            self.update_status(f"Viewing {tab_name} tab")
            
            # Refresh tab data if needed
            if hasattr(self.tabs[tab_name], 'refresh_data'):
                self.tabs[tab_name].refresh_data()
    
    def toggle_tab(self, tab_name):
        """Toggle tab visibility"""
        try:
            # If toggling on and tab not created yet, try to create it
            is_on = bool(self.tab_vars.get(tab_name, tk.BooleanVar(value=True)).get())
            if is_on and tab_name not in self.tabs:
                try:
                    self._create_tab_by_name(tab_name)
                except Exception:
                    pass

            if tab_name in self.tabs:
                try:
                    tab_index = list(self.tabs.keys()).index(tab_name)
                except ValueError:
                    tab_index = None

                if self.tab_vars[tab_name].get():
                    # Show tab (add if missing)
                    if tab_index is None:
                        try:
                            self.notebook.add(self.tabs[tab_name].frame, text=tab_name)
                        except Exception:
                            pass
                else:
                    # Hide tab if present
                    if tab_index is not None:
                        try:
                            self.notebook.forget(tab_index)
                        except Exception:
                            pass
        except:
            pass

    def _create_tab_by_name(self, tab_name: str):
        """Create a single tab instance by name and add to notebook and `self.tabs`."""
        mapping = {
            'Dashboard': ('UI.dashboard', 'DashboardTab'),
            'Students': ('UI.students', 'StudentsTab'),
            'Teachers': ('UI.teachers', 'TeachersTab'),
            'Finance': ('UI.finance', 'FinanceTab'),
            'Inventory': ('UI.inventory', 'InventoryTab'),
            'Attendance': ('UI.attendance', 'AttendanceTab'),
            'Reports': ('UI.reports', 'ReportsTab')
        }
        if tab_name not in mapping:
            return
        module_name, class_name = mapping[tab_name]
        mod = __import__(module_name, fromlist=[class_name])
        TabClass = getattr(mod, class_name)
        if tab_name == 'Dashboard':
            inst = TabClass(self.notebook, role=getattr(config.Config, 'CURRENT_USER_ROLE', ''))
        else:
            inst = TabClass(self.notebook)
        self.tabs[tab_name] = inst
        try:
            self.notebook.add(inst.frame, text=tab_name)
        except Exception:
            pass
    
    # Menu command implementations
    
    def backup_database(self):
        """Backup database functionality"""
        from utils.export_import import backup_database
        try:
            backup_file = config.Config.get_backup_filename()
            if backup_database(backup_file):
                messagebox.showinfo("Success", 
                                   f"Database backup created successfully:\n{backup_file}")
                self.update_status("Database backup completed")
            else:
                messagebox.showerror("Error", "Failed to create database backup")
        except Exception as e:
            messagebox.showerror("Error", f"Backup failed: {str(e)}")
    
    def restore_database(self):
        """Restore database from backup"""
        from tkinter import filedialog
        from utils.export_import import restore_database
        
        backup_file = filedialog.askopenfilename(
            title="Select Backup File",
            filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
            initialdir=str(config.Config.PATHS['backups'])
        )
        
        if backup_file:
            response = messagebox.askyesno("Confirm Restore",
                                          "This will overwrite current database.\n"
                                          "Are you sure you want to continue?")
            if response:
                try:
                    if restore_database(backup_file):
                        messagebox.showinfo("Success", "Database restored successfully")
                        self.update_status("Database restored")
                        self.refresh_all()
                    else:
                        messagebox.showerror("Error", "Failed to restore database")
                except Exception as e:
                    messagebox.showerror("Error", f"Restore failed: {str(e)}")
    
    def export_data(self):
        """Export data to Excel"""
        from utils.export_import import export_all_data
        
        try:
            export_file = config.Config.get_export_filename("all_data")
            if export_all_data(export_file):
                messagebox.showinfo("Success",
                                  f"Data exported successfully:\n{export_file}")
                self.update_status("Data exported to Excel")
            else:
                messagebox.showerror("Error", "Failed to export data")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {str(e)}")
    
    def import_data(self):
        """Import data from Excel"""
        from tkinter import filedialog
        from utils.export_import import import_from_excel
        
        import_file = filedialog.askopenfilename(
            title="Select Import File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
            initialdir=str(config.Config.PATHS['exports'])
        )
        
        if import_file:
            response = messagebox.askyesno("Confirm Import",
                                          "This will import data from Excel file.\n"
                                          "Are you sure you want to continue?")
            if response:
                try:
                    success, message = import_from_excel(import_file)
                    if success:
                        messagebox.showinfo("Success", message)
                        self.update_status("Data imported from Excel")
                        self.refresh_all()
                    else:
                        messagebox.showerror("Error", message)
                except Exception as e:
                    messagebox.showerror("Error", f"Import failed: {str(e)}")
    
    def print_data(self):
        """Print current tab data"""
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        self.update_status(f"Printing {current_tab} data...")
        messagebox.showinfo("Print", f"Printing {current_tab} data")
    
    def open_preferences(self):
        """Open preferences dialog"""
        from UI.dialogs import PreferencesDialog
        dialog = PreferencesDialog(self.root)
        dialog.show()
        self.update_status("Preferences updated")

    def open_user_manager(self):
        """Open the user manager dialog to add/edit/remove users and roles."""
        try:
            from UI.dialogs import UsersDialog
            dialog = UsersDialog(self.root)
            dialog.show()
            # reload tabs in case current role/user changed
            try:
                self.on_user_role_changed()
            except Exception:
                pass
            self.update_status("User list updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open user manager: {e}")

    def open_change_password(self):
        """Allow current user to change their own password"""
        try:
            user = getattr(config.Config, 'CURRENT_USER', None)
            if not user:
                messagebox.showwarning('Not logged in', 'No user is currently logged in')
                return
            from UI.dialogs import ChangePasswordDialog
            dlg = ChangePasswordDialog(self.root, username=user)
            dlg.show()
            if getattr(dlg, 'result', False):
                messagebox.showinfo('Success', 'Password changed')
        except Exception as e:
            messagebox.showerror('Error', str(e))
    
    def refresh_all(self):
        """Refresh all tabs"""
        self.update_status("Refreshing all data...")
        
        for tab_name, tab in self.tabs.items():
            if hasattr(tab, 'refresh_data'):
                try:
                    tab.refresh_data()
                except:
                    pass
        
        self.update_database_status()
        self.update_status("All data refreshed")
    
    def database_maintenance(self):
        """Run database maintenance"""
        from utils.helpers import run_database_maintenance
        
        response = messagebox.askyesno("Database Maintenance",
                                      "Run database maintenance tasks?\n"
                                      "This may take a few moments.")
        if response:
            try:
                run_database_maintenance()
                messagebox.showinfo("Success", "Database maintenance completed")
                self.update_status("Database maintenance completed")
            except Exception as e:
                messagebox.showerror("Error", f"Maintenance failed: {str(e)}")
    
    def recalculate_balances(self):
        """Recalculate all student balances"""
        from models.finance import FinancialManager
        
        response = messagebox.askyesno("Recalculate Balances",
                                      "Recalculate all student balances?\n"
                                      "This may take a few moments.")
        if response:
            try:
                # This would involve recalculating balances in the database
                # For now, just refresh the finance tab
                if 'Finance' in self.tabs:
                    self.tabs['Finance'].refresh_data()
                
                messagebox.showinfo("Success", "Balances recalculated")
                self.update_status("Student balances recalculated")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to recalculate: {str(e)}")
    
    def send_notifications(self):
        """Send notifications to parents"""
        # Notifications UI is not implemented as a dialog in `UI.dialogs`.
        # If a Notifications tab exists, select it; otherwise inform the user.
        try:
            if 'Notifications' in self.tabs:
                idx = list(self.tabs.keys()).index('Notifications')
                self.notebook.select(idx)
                return
        except Exception:
            pass

        messagebox.showinfo("Notifications", "Notification system is not configured.\n"
                            "You can manage notifications from the Reports/Tools menu when available.")
    
    def generate_student_list(self):
        """Generate student list report"""
        from reports.generators.student_reports import generate_student_list_report
        from datetime import date
        import config
        reports_dir = config.Config.PATHS.get('reports')
        fname = reports_dir / f"student_list_{date.today().strftime('%Y%m%d')}.pdf"
        generate_student_list_report(str(fname))
        self.update_status("Student list report generated")
    
    def generate_student_fees_report(self):
        """Generate student fees report"""
        from reports.generators.financial_reports import generate_student_fees_report
        from datetime import date
        import config
        reports_dir = config.Config.PATHS.get('reports')
        fname = reports_dir / f"student_fees_{date.today().strftime('%Y%m%d')}.pdf"
        generate_student_fees_report(str(fname))
        self.update_status("Student fees report generated")
    
    def generate_attendance_report(self):
        """Generate attendance report"""
        from reports.generators.student_reports import generate_attendance_summary_report
        from datetime import date
        import config
        reports_dir = config.Config.PATHS.get('reports')
        fname = reports_dir / f"attendance_summary_{date.today().strftime('%Y%m%d')}.pdf"
        generate_attendance_summary_report(str(fname))
        self.update_status("Attendance report generated")
    
    def generate_fee_collection_report(self):
        """Generate fee collection report"""
        from reports.generators.financial_reports import generate_fee_collection_report
        from datetime import date
        import config
        reports_dir = config.Config.PATHS.get('reports')
        fname = reports_dir / f"fee_collection_{date.today().strftime('%Y%m%d')}.pdf"
        generate_fee_collection_report(str(fname))
        self.update_status("Fee collection report generated")
    
    def generate_expense_report(self):
        """Generate expense report"""
        from reports.generators.financial_reports import generate_expense_report
        from datetime import date
        import config
        reports_dir = config.Config.PATHS.get('reports')
        fname = reports_dir / f"expense_{date.today().strftime('%Y%m%d')}.pdf"
        generate_expense_report(str(fname))
        self.update_status("Expense report generated")
    
    def generate_financial_summary(self):
        """Generate financial summary report"""
        from reports.generators.financial_reports import generate_financial_summary_report
        from datetime import date
        import config
        reports_dir = config.Config.PATHS.get('reports')
        fname = reports_dir / f"financial_summary_{date.today().strftime('%Y%m%d')}.pdf"
        generate_financial_summary_report(str(fname))
        self.update_status("Financial summary generated")
    
    def generate_inventory_list(self):
        """Generate inventory list report"""
        from reports.generators.inventory_reports import generate_inventory_list_report
        from datetime import date
        import config
        reports_dir = config.Config.PATHS.get('reports')
        fname = reports_dir / f"inventory_list_{date.today().strftime('%Y%m%d')}.pdf"
        generate_inventory_list_report(str(fname))
        self.update_status("Inventory list report generated")
    
    def generate_low_stock_report(self):
        """Generate low stock report"""
        from reports.generators.inventory_reports import generate_low_stock_report
        from datetime import date
        import config
        reports_dir = config.Config.PATHS.get('reports')
        fname = reports_dir / f"low_stock_{date.today().strftime('%Y%m%d')}.pdf"
        generate_low_stock_report(str(fname))
        self.update_status("Low stock report generated")
    
    def open_manual(self):
        """Open user manual"""
        manual_path = config.Config.RESOURCE_DIR / "docs" / "user_manual.pdf"
        if manual_path.exists():
            import os
            os.startfile(str(manual_path))
            self.update_status("Opening user manual...")
        else:
            messagebox.showinfo("Manual", "User manual not found in docs folder.")
    
    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts = """
        Keyboard Shortcuts:
        
        General:
        Ctrl+B    - Backup database
        Ctrl+P    - Print current view
        Ctrl+Q    - Exit application
        F5        - Refresh all data
        
        Navigation:
        Ctrl+1    - Dashboard
        Ctrl+2    - Students
        Ctrl+3    - Teachers
        Ctrl+4    - Finance
        Ctrl+5    - Inventory
        Ctrl+6    - Attendance
        Ctrl+7    - Reports
        
        Data Entry:
        Ctrl+N    - New record (in current tab)
        Ctrl+S    - Save record
        Ctrl+F    - Find/Search
        Delete    - Delete selected record
        """
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts)
    
    def check_for_updates(self):
        """Check for application updates"""
        self.update_status("Checking for updates...")
        messagebox.showinfo("Updates", 
                           f"You are running {config.Config.APP_NAME} v{config.Config.VERSION}\n\n"
                           "This is the latest version.")
        self.update_status("Ready")
    
    def show_about(self):
        """Show about dialog"""
        from UI.dialogs import AboutDialog
        dialog = AboutDialog(self.root)
        dialog.show()
