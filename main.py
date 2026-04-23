#!/usr/bin/env python3
"""
School Management System - Main Entry Point
"""
import tkinter as tk
from tkinter import messagebox
import sys
import os
import config

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import DatabaseConnection
from UI.main_window import MainWindow
from utils.helpers import check_database_connection, setup_logging

class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.db_connection = None
        self.setup_application()
        
    def setup_application(self):
        """Setup application window and database connection"""
        try:
            setup_logging()
            config.Config.log_runtime_context("application_setup")

            # Check database connection
            if not check_database_connection():
                response = messagebox.askyesno(
                    "Database Connection Failed",
                    "Failed to connect to database. Would you like to run in offline mode?\n\n"
                    "Note: Some features may be limited."
                )
                if not response:
                    sys.exit(0)
            
            # Initialize main window
            # Apply theme settings
            try:
                from tkinter import ttk
                style = ttk.Style(self.root)
                # Use configured theme
                theme = getattr(__import__('config').Config, 'UI', {}).get('theme', 'clam')
                style.theme_use(theme)

                # Dark mode adjustments
                if getattr(__import__('config').Config, 'THEME_MODE', 'light') == 'dark':
                    style.configure('.', background='#2b2b2b', foreground='#e6e6e6')
                    style.configure('TLabel', background='#2b2b2b', foreground='#e6e6e6')
                    style.configure('TFrame', background='#2b2b2b')
                    style.configure('Treeview', background='#222222', fieldbackground='#222222', foreground='#e6e6e6')
            except Exception:
                pass

            self.main_window = MainWindow(self.root)
            
            # Set window properties
            self.root.title("Hope Academy Primary School Management System")
            self.root.geometry("1200x700")
            self.root.minsize(1000, 600)
            
            # Center window on screen
            self.center_window()
            
            # Set application icon if available
            self.set_window_icon()
            
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(tb)
            messagebox.showerror("Initialization Error", f"Failed to initialize application: {str(e)}\nSee console for traceback.")
            sys.exit(1)
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def set_window_icon(self):
        """Set application icon"""
        try:
            icon_path = config.Config.PATHS.get('assets', config.Config.RESOURCE_DIR / 'assets') / 'icons' / 'app_icon.ico'
            if os.path.exists(icon_path):
                self.root.iconbitmap(str(icon_path))
            else:
                # Override default Tk icon with an empty image to remove the tkinter symbol
                try:
                    img = tk.PhotoImage()
                    self.root.iconphoto(False, img)
                except Exception:
                    pass
        except:
            pass  # Icon not essential
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        if self.db_connection:
            self.db_connection.close()

def main():
    """Main function"""
    app = Application()
    app.run()

if __name__ == "__main__":
    main()
