#!/usr/bin/env python3
"""
School Management System - Main Entry Point
"""
import os
import sys

# Make project packages importable regardless of the launch directory.
# This must run before any project import below.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import messagebox, ttk

import config
from database.connection import db
from UI.main_window import MainWindow
from utils.helpers import check_database_connection, setup_logging


class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_application()

    def setup_application(self):
        """Setup application window and database connection"""
        try:
            setup_logging()
            config.Config.log_runtime_context("application_setup")
            self.apply_theme()

            if not config.Config.DB_BACKEND:
                # First launch on this computer: ask where to keep the data.
                from UI.first_run import FirstRunDialog
                self.root.withdraw()
                if not FirstRunDialog(self.root).show():
                    sys.exit(0)
                self.root.deiconify()

            self.prepare_database()
            self.main_window = MainWindow(self.root)

            self.root.title("Hope Academy Primary School Management System")
            self.root.geometry("1200x700")
            self.root.minsize(1000, 600)
            self.center_window()
            self.set_window_icon()

        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Application failed to start")
            messagebox.showerror("The program could not start",
                                 f"{e}\n\nTechnical details were written to:\n{config.Config.get_log_file()}")
            sys.exit(1)

    def prepare_database(self):
        """Open the chosen storage, creating or upgrading it if needed."""
        if config.Config.DB_BACKEND == 'sqlite':
            # Creates the data file on first use and upgrades files from older versions.
            db.prepare()
            try:
                from utils.export_import import run_automatic_backup
                run_automatic_backup()
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Automatic backup failed")
            return

        if not check_database_connection():
            cfg = config.Config.DB_CONFIG
            if not messagebox.askyesno(
                "Cannot reach the MySQL server",
                f"The program could not connect to the MySQL server at {cfg.get('host')}.\n\n"
                "Check that MySQL is running, then start the program again.\n\n"
                "Open the program anyway? (Most screens will be empty.)"
            ):
                sys.exit(0)

    def apply_theme(self):
        """Apply the configured ttk theme and optional dark mode."""
        try:
            style = ttk.Style(self.root)
            style.theme_use(config.Config.UI.get('theme', 'clam'))
            if config.Config.THEME_MODE == 'dark':
                style.configure('.', background='#2b2b2b', foreground='#e6e6e6')
                style.configure('TLabel', background='#2b2b2b', foreground='#e6e6e6')
                style.configure('TFrame', background='#2b2b2b')
                style.configure('Treeview', background='#222222', fieldbackground='#222222',
                                foreground='#e6e6e6')
        except tk.TclError:
            pass  # unknown theme name: keep the platform default

    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def set_window_icon(self):
        """Set the application icon (bundled as assets/app.ico)."""
        icon_path = config.Config.PATHS['assets'] / 'app.ico'
        try:
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
            else:
                # Hide the default Tk feather rather than show a wrong icon.
                self.root.iconphoto(False, tk.PhotoImage())
        except tk.TclError:
            pass  # icon is cosmetic

    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def cleanup(self):
        """Release database connections."""
        db.close()


def main():
    """Main function"""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
