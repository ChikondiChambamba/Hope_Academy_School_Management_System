"""
Main application window
"""
import tkinter as tk
from tkinter import ttk, Menu, messagebox
import config
from database.connection import db
import os

class MainWindow:
    # Tab name -> permission feature required to see it.
    TAB_FEATURES = {
        'Dashboard': 'dashboard',
        'Students': 'students',
        'Teachers': 'teachers',
        'Finance': 'finance',
        'Inventory': 'inventory',
        'Attendance': 'attendance',
        'Reports': 'reports',
    }

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

        # Create tabs permitted for the current role
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
        self._update_session_status()

        # Login is switched on and nobody is logged in yet: ask for credentials
        # once the main window is on screen.
        if config.Config.login_required() and not config.Config.CURRENT_USER:
            self.root.after(200, self.show_login)
            # While the user types their password, pay Tk's one-off emoji font
            # lookup so the dashboard appears promptly after logging in.
            from UI.dashboard import warm_up_icon_font
            self.root.after(400, lambda: warm_up_icon_font(self.root))
    
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
        login_on = config.Config.login_required()
        if login_on:
            file_menu.add_command(label="Login",
                     command=self.show_login,
                     accelerator="Ctrl+I")
            file_menu.add_command(label="Logout",
                     command=self.logout,
                     accelerator="Ctrl+L")
            file_menu.add_separator()
        file_menu.add_command(label="Exit",
                             command=self.root.quit,
                             accelerator="Ctrl+Q")

        # Edit menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Preferences",
                             command=self.open_preferences)
        if login_on:
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
        for tab_name, feature in self.TAB_FEATURES.items():
            allowed = config.Config.has_permission(feature)
            var = tk.BooleanVar(value=allowed)
            self.tab_vars[tab_name] = var
            view_menu.add_checkbutton(label=tab_name,
                                      variable=var,
                                      state='normal' if allowed else 'disabled',
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
        if login_on:
            self.root.bind('<Control-i>', lambda e: self.show_login())
            self.root.bind('<Control-l>', lambda e: self.logout())
        else:
            self.root.unbind('<Control-i>')
            self.root.unbind('<Control-l>')
        self.root.bind('<Control-u>', lambda e: self.open_user_manager())
        self.root.bind('<F5>', lambda e: self.refresh_all())

    def logout(self):
        """End the current session and drop to the logged-out (no access) view."""
        try:
            config.Config.logout()
            self.on_user_role_changed()
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
            self.create_menu_bar()
            self.create_tabs()
            self._update_session_status()
        except Exception:
            pass

    def _update_session_status(self):
        user = config.Config.CURRENT_USER
        role = config.Config.CURRENT_USER_ROLE
        if user:
            self.update_status(f"Logged in as {user} ({role})")
        elif role:
            self.update_status("Ready")
        else:
            self.update_status("Not logged in - use File > Login (Ctrl+I)")

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
        """Show the login dialog (modal).

        A successful login fires <<UserRoleChanged>>, which rebuilds menus and
        tabs for the new role; a cancelled login changes nothing.
        """
        if not config.Config.login_required():
            return
        from UI.dialogs import LoginDialog
        LoginDialog(self.root).show()
    
    def create_tabs(self):
        """Create the notebook with one page per tab the current role may see.

        Only the first page is built now; every other tab is built the first
        time it is opened, so logging in shows the window without waiting for
        all seven tabs to load their data.
        """
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill='both', expand=True)
        self.tabs = {}     # tab name -> built tab instance
        self._pages = {}   # tab name -> page frame in the notebook (content built lazily)
        self._skip_refresh = None

        for name, feature in self.TAB_FEATURES.items():
            if not config.Config.has_permission(feature):
                continue
            page = ttk.Frame(self.notebook)
            self._pages[name] = page
            self.notebook.add(page, text=name)
            var = self.tab_vars.get(name)
            if var is not None and not var.get():
                self.notebook.hide(page)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        visible = [n for n, p in self._pages.items() if self.notebook.tab(p, 'state') != 'hidden']
        if visible:
            self.notebook.select(self._pages[visible[0]])
            self._build_tab(visible[0])
            self._skip_refresh = visible[0]   # just loaded; the selection event needn't reload it

    @staticmethod
    def _tab_class(name):
        # Explicit imports (not importlib) so PyInstaller bundles every tab module.
        if name == 'Dashboard':
            from UI.dashboard import DashboardTab
            return DashboardTab
        if name == 'Students':
            from UI.students import StudentsTab
            return StudentsTab
        if name == 'Teachers':
            from UI.teachers import TeachersTab
            return TeachersTab
        if name == 'Finance':
            from UI.finance import FinanceTab
            return FinanceTab
        if name == 'Inventory':
            from UI.inventory import InventoryTab
            return InventoryTab
        if name == 'Attendance':
            from UI.attendance import AttendanceTab
            return AttendanceTab
        if name == 'Reports':
            from UI.reports import ReportsTab
            return ReportsTab
        raise KeyError(name)

    def _build_tab(self, name):
        """Build a tab's content inside its page (once). Returns (tab, newly_built)."""
        if name in self.tabs:
            return self.tabs[name], False
        page = self._pages[name]
        self.root.config(cursor='watch')
        self.root.update_idletasks()
        try:
            TabClass = self._tab_class(name)
            if name == 'Dashboard':
                tab = TabClass(page, role=getattr(config.Config, 'CURRENT_USER_ROLE', ''))
            else:
                tab = TabClass(page)
            tab.frame.pack(fill='both', expand=True)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Could not open the %s tab", name)
            ttk.Label(page, text=f"The {name} tab could not be opened:\n{e}", padding=20).pack()
            tab = None
        finally:
            self.root.config(cursor='')
        if tab is not None:
            self.tabs[name] = tab
        return tab, True

    def _selected_tab_name(self):
        try:
            selected = self.notebook.select()
        except tk.TclError:
            return None
        return next((n for n, p in self._pages.items() if str(p) == str(selected)), None)

    def on_tab_change(self, event):
        """Build a tab the first time it is opened; refresh it on later visits."""
        name = self._selected_tab_name()
        if not name:
            return
        self.update_status(f"Viewing {name} tab")
        tab, newly_built = self._build_tab(name)
        if self._skip_refresh == name:
            self._skip_refresh = None
            return
        if tab is not None and not newly_built and hasattr(tab, 'refresh_data'):
            tab.refresh_data()

    def toggle_tab(self, tab_name):
        """Show or hide a tab from the View menu (only tabs the current role may see)."""
        feature = self.TAB_FEATURES.get(tab_name)
        if feature and not config.Config.has_permission(feature):
            self.tab_vars[tab_name].set(False)
            self._require(feature)
            return
        page = self._pages.get(tab_name)
        if page is None:
            return
        if self.tab_vars[tab_name].get():
            self.notebook.add(page)      # re-adding a hidden page restores it in place
        else:
            self.notebook.hide(page)

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
        """Show whether the school data can be reached (one label, updated in place)."""
        local = config.Config.DB_BACKEND == 'sqlite'
        if db.test_connection():
            status_text = "Data: saved on this computer ✓" if local else "Database: Connected ✓"
            status_color = 'green'
        else:
            status_text = "Data: cannot be opened ✗" if local else "Database: Disconnected ✗"
            status_color = 'red'

        if getattr(self, 'db_status_label', None) is None:
            self.db_status_label = ttk.Label(self.status_bar, relief='sunken', padding=(5, 2))
            self.db_status_label.pack(side='right', padx=(0, 10))
        self.db_status_label.configure(text=status_text, foreground=status_color)
    
    def update_status(self, message: str):
        """Update status bar message"""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def _require(self, feature: str) -> bool:
        """Return True if the current role may use `feature`, else explain why not."""
        if config.Config.has_permission(feature):
            return True
        if not config.Config.CURRENT_USER and config.Config.login_required():
            messagebox.showwarning("Login Required", "Please log in first (File > Login).")
        else:
            messagebox.showwarning("Access Denied",
                                   "Your role does not have access to this feature.")
        return False

    # Menu command implementations
    
    def backup_database(self):
        """Save a full copy of the school data."""
        if not self._require('settings'):
            return
        from utils.export_import import backup_database, backup_extension
        from datetime import datetime
        backup_file = config.Config.PATHS['backups'] / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{backup_extension()}"
        if backup_database(str(backup_file)):
            messagebox.showinfo("Backup Complete", f"A backup of your data was saved to:\n{backup_file}")
            self.update_status("Backup completed")
        else:
            messagebox.showerror("Backup Failed",
                                 "The backup could not be created. See the log file for details.")

    def restore_database(self):
        """Replace the current data with a previously saved backup."""
        if not self._require('settings'):
            return
        from tkinter import filedialog
        from utils.export_import import restore_database, backup_extension

        ext = backup_extension()
        label = "School data backups" if ext == ".db" else "SQL backups"
        backup_file = filedialog.askopenfilename(
            title="Choose a backup to restore",
            filetypes=[(label, f"*{ext}"), ("All files", "*.*")],
            initialdir=str(config.Config.PATHS['backups'])
        )
        if not backup_file:
            return
        if not messagebox.askyesno("Confirm Restore",
                                   "All current data will be replaced by the selected backup.\n\n"
                                   "Continue?"):
            return
        ok, message = restore_database(backup_file)
        if ok:
            messagebox.showinfo("Restore Complete", message)
            self.update_status("Data restored from backup")
            self.on_user_role_changed()   # rebuild every tab from the restored data
        else:
            messagebox.showerror("Restore Failed", message)

    def export_data(self):
        """Export every table to CSV files (opens in Excel)."""
        if not self._require('settings'):
            return
        from utils.export_import import export_all_data
        folder = export_all_data()
        if folder:
            messagebox.showinfo("Export Complete", f"All data was exported as CSV files to:\n{folder}")
            self.update_status("Data exported")
        else:
            messagebox.showerror("Export Failed", "The data could not be exported. See the log file for details.")

    def import_data(self):
        """Bulk import (not available yet)."""
        if not self._require('settings'):
            return
        from utils.export_import import import_from_excel
        _, message = import_from_excel(None)
        messagebox.showinfo("Import", message)

    def print_data(self):
        """Direct printing is not implemented; point users to the PDF reports."""
        messagebox.showinfo("Print",
                            "Direct printing is not available.\n\n"
                            "Generate a PDF from the Reports menu (or a tab's report/export "
                            "button) and print it from your PDF viewer.")
    
    def open_preferences(self):
        """Open preferences dialog"""
        if not self._require('settings'):
            return
        from UI.dialogs import PreferencesDialog
        dialog = PreferencesDialog(self.root)
        dialog.show()
        self.update_status("Preferences updated")

    def open_user_manager(self):
        """Open the user manager dialog to add/edit/remove users and roles."""
        if not self._require('manage_users'):
            return
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
        if not self._require('settings'):
            return
        from utils.helpers import run_database_maintenance
        
        response = messagebox.askyesno("Database Maintenance",
                                      "Check the database and tidy it up?\n"
                                      "No records are changed or deleted.")
        if response:
            ok, message = run_database_maintenance()
            (messagebox.showinfo if ok else messagebox.showerror)("Database Maintenance", message)
            self.update_status("Database maintenance completed" if ok else "Database maintenance failed")

    def recalculate_balances(self):
        """Recalculate all student balances"""
        if not self._require('finance'):
            return
        response = messagebox.askyesno("Recalculate Balances",
                                      "Recalculate all student balances?\n"
                                      "This may take a few moments.")
        if response:
            try:
                # Balances are not stored; FinancialManager derives them from fee
                # and payment rows on every read, so "recalculating" means
                # reloading the views that display them.
                self.refresh_all()
                messagebox.showinfo("Balances Refreshed",
                                    "Balances are calculated live from fees and payments.\n"
                                    "All views have been reloaded with current figures.")
                self.update_status("Student balances refreshed")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to refresh balances: {str(e)}")
    
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
    
    def _run_report(self, feature: str, label: str, prefix: str, generator, **kwargs):
        """Permission-check, generate a dated PDF in the reports folder, and report the outcome."""
        if not self._require(feature):
            return
        from datetime import date
        reports_dir = config.Config.PATHS['reports']
        reports_dir.mkdir(parents=True, exist_ok=True)
        fname = reports_dir / f"{prefix}_{date.today().strftime('%Y%m%d')}.pdf"
        try:
            generator(str(fname), **kwargs)
        except Exception as e:
            messagebox.showerror("Report Failed", f"Could not generate the {label}:\n{e}")
            self.update_status(f"{label} failed")
            return
        self.update_status(f"{label} generated")
        messagebox.showinfo("Report Generated", f"{label} saved to:\n{fname}")

    def generate_student_list(self):
        from reports.generators.student_reports import generate_student_list_report
        self._run_report('students', "Student list", "student_list", generate_student_list_report)

    def generate_attendance_report(self):
        from reports.generators.student_reports import generate_attendance_summary_report
        self._run_report('attendance', "Attendance report", "attendance_summary",
                         generate_attendance_summary_report)

    def generate_student_fees_report(self):
        from reports.generators.financial_reports import generate_student_fees_report
        self._run_report('financial_reports', "Student fees report", "student_fees",
                         generate_student_fees_report)

    def generate_fee_collection_report(self):
        from reports.generators.financial_reports import generate_fee_collection_report
        self._run_report('financial_reports', "Fee collection report", "fee_collection",
                         generate_fee_collection_report)

    def generate_expense_report(self):
        from reports.generators.financial_reports import generate_expense_report
        safe_term = str(config.Config.CURRENT_TERM).replace(' ', '_')
        self._run_report('financial_reports', "Expense report", f"expense_{safe_term}",
                         generate_expense_report,
                         academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
                         term=config.Config.CURRENT_TERM)

    def generate_financial_summary(self):
        from reports.generators.financial_reports import generate_financial_summary_report
        self._run_report('financial_reports', "Financial summary", "financial_summary",
                         generate_financial_summary_report)

    def generate_inventory_list(self):
        from reports.generators.inventory_reports import generate_inventory_list_report
        self._run_report('inventory', "Inventory list", "inventory_list", generate_inventory_list_report)

    def generate_low_stock_report(self):
        from reports.generators.inventory_reports import generate_low_stock_report
        self._run_report('inventory', "Low stock report", "low_stock", generate_low_stock_report)
    
    def open_manual(self):
        """Open user manual"""
        manual_path = config.Config.RESOURCE_DIR / "docs" / "user_manual.pdf"
        if manual_path.exists():
            os.startfile(str(manual_path))
            self.update_status("Opening user manual...")
        else:
            messagebox.showinfo("Manual", "User manual not found in docs folder.")
    
    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        # Keep in sync with the bindings in create_menu_bar().
        lines = ["Keyboard Shortcuts:", ""]
        if config.Config.login_required():
            lines += ["Ctrl+I    - Login", "Ctrl+L    - Logout"]
        lines += ["Ctrl+U    - Manage users", "Ctrl+B    - Backup database", "Ctrl+P    - Print current view",
                  "Ctrl+Q    - Exit application", "F5        - Refresh all data"]
        messagebox.showinfo("Keyboard Shortcuts", "\n".join(lines))
    
    def check_for_updates(self):
        """Check for application updates"""
        messagebox.showinfo("Updates",
                           f"You are running {config.Config.APP_NAME} v{config.Config.VERSION}.\n\n"
                           "Automatic update checks are not available. "
                           "Contact your system administrator for new releases.")
    
    def show_about(self):
        """Show about dialog"""
        from UI.dialogs import AboutDialog
        dialog = AboutDialog(self.root)
        dialog.show()
