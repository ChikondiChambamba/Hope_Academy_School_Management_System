"""First-launch setup: choose where data is stored and (optionally) create a login.

Written for non-technical users: the recommended choice is preselected and
needs no further input; MySQL is offered only as an advanced option.
"""
import tkinter as tk
from tkinter import messagebox, ttk

import config
from database.connection import db

PAD = {'padx': 12, 'pady': 4}


class FirstRunDialog:
    def __init__(self, parent):
        self.parent = parent
        self.completed = False
        self.win = tk.Toplevel(parent)
        self.win.title("Welcome")
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.on_exit)
        self._build()
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        x = (self.win.winfo_screenwidth() - w) // 2
        y = max((self.win.winfo_screenheight() - h) // 3, 0)
        self.win.geometry(f"+{x}+{y}")
        self.win.grab_set()
        self.win.focus_force()

    # layout
    def _build(self):
        body = ttk.Frame(self.win, padding=16)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text=f"Welcome to {config.Config.APP_NAME}",
                  font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(body, text="Two quick questions and you are ready to start.",
                  foreground='#555').pack(anchor='w', pady=(2, 12))

        # 1. storage
        storage = ttk.LabelFrame(body, text=" 1. Where should the school's information be saved? ", padding=10)
        storage.pack(fill='x')
        self.backend_var = tk.StringVar(value='sqlite')
        ttk.Radiobutton(storage, text="On this computer (recommended)", value='sqlite',
                        variable=self.backend_var, command=self._toggle_mysql).pack(anchor='w')
        ttk.Label(storage, text="Everything is kept in one file on this computer. Nothing else to install.\n"
                                "Backups are made automatically every day.",
                  foreground='#555').pack(anchor='w', padx=(22, 0), pady=(0, 8))
        ttk.Radiobutton(storage, text="On a MySQL server (advanced)", value='mysql',
                        variable=self.backend_var, command=self._toggle_mysql).pack(anchor='w')
        ttk.Label(storage, text="Only choose this if someone has already set up a MySQL server for you.",
                  foreground='#555').pack(anchor='w', padx=(22, 0))

        self.mysql_frame = ttk.Frame(storage, padding=(22, 8, 0, 0))
        cfg = config.Config.DB_CONFIG
        self.mysql_vars = {
            'host': tk.StringVar(value=cfg.get('host') or 'localhost'),
            'port': tk.StringVar(value=str(cfg.get('port') or 3306)),
            'user': tk.StringVar(value=cfg.get('user') or 'root'),
            'password': tk.StringVar(value=''),
            'database': tk.StringVar(value=cfg.get('database') or 'school_management'),
        }
        for row, (key, label) in enumerate([('host', 'Server'), ('port', 'Port'), ('user', 'Username'),
                                            ('password', 'Password'), ('database', 'Database name')]):
            ttk.Label(self.mysql_frame, text=label + ":").grid(row=row, column=0, sticky='e', pady=2)
            ttk.Entry(self.mysql_frame, textvariable=self.mysql_vars[key], width=28,
                      show='*' if key == 'password' else '').grid(row=row, column=1, sticky='w', padx=6, pady=2)
        ttk.Button(self.mysql_frame, text="Test connection", command=self._test_mysql).grid(
            row=5, column=1, sticky='w', padx=6, pady=(6, 0))
        self.mysql_status = ttk.Label(self.mysql_frame, text='', wraplength=330)
        self.mysql_status.grid(row=6, column=0, columnspan=2, sticky='w', pady=(4, 0))

        # 2. login
        login = ttk.LabelFrame(body, text=" 2. Protect the program with a login (optional) ", padding=10)
        login.pack(fill='x', pady=(12, 0))
        ttk.Label(login, text="If other people use this computer, create a login so only you can open\n"
                              "the school records. Leave these empty to skip; you can add one later\n"
                              "under Edit > Manage Users.",
                  foreground='#555').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))
        self.user_var, self.pwd_var, self.pwd2_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for row, (label, var, secret) in enumerate([("Your name", self.user_var, False),
                                                    ("Password", self.pwd_var, True),
                                                    ("Repeat password", self.pwd2_var, True)], start=1):
            ttk.Label(login, text=label + ":").grid(row=row, column=0, sticky='e', pady=2)
            ttk.Entry(login, textvariable=var, width=28, show='*' if secret else '').grid(
                row=row, column=1, sticky='w', padx=6, pady=2)

        buttons = ttk.Frame(body)
        buttons.pack(fill='x', pady=(16, 0))
        self.start_button = ttk.Button(buttons, text="Start", command=self.on_start)
        self.start_button.pack(side='right')
        ttk.Button(buttons, text="Exit", command=self.on_exit).pack(side='right', padx=(0, 8))
        self.win.bind('<Return>', lambda e: self.on_start())

    def _toggle_mysql(self):
        if self.backend_var.get() == 'mysql':
            self.mysql_frame.pack(fill='x')
        else:
            self.mysql_frame.pack_forget()

    # MySQL helpers
    def _mysql_settings(self):
        values = {k: v.get().strip() for k, v in self.mysql_vars.items()}
        values['password'] = self.mysql_vars['password'].get()
        if not values['host'] or not values['user'] or not values['database']:
            raise ValueError("Please fill in the server, username and database name.")
        try:
            values['port'] = int(values['port'] or 3306)
        except ValueError:
            raise ValueError("The port must be a number (usually 3306).")
        values['autocommit'] = True
        return values

    def _mysql_state(self, settings):
        """Return 'ready', 'empty' (database missing or has no tables)."""
        import mysql.connector
        server = {k: v for k, v in settings.items() if k != 'database'}
        conn = mysql.connector.connect(connection_timeout=5, **server)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'students'",
                        (settings['database'],))
            return 'ready' if cur.fetchall() else 'empty'
        finally:
            conn.close()

    def _test_mysql(self):
        try:
            state = self._mysql_state(self._mysql_settings())
        except ValueError as e:
            self.mysql_status.configure(text=str(e), foreground='#b00020')
            return
        except Exception as e:
            self.mysql_status.configure(text=f"Could not connect: {e}", foreground='#b00020')
            return
        text = ("Connected. The school database was found." if state == 'ready'
                else "Connected. The database will be created when you press Start.")
        self.mysql_status.configure(text=text, foreground='#1b5e20')

    # actions
    def _validate_login(self):
        name, pwd, pwd2 = self.user_var.get().strip(), self.pwd_var.get(), self.pwd2_var.get()
        if not name and not pwd and not pwd2:
            return None
        if not name:
            raise ValueError("Please enter your name for the login, or clear the password fields to skip.")
        if not pwd:
            raise ValueError("Please choose a password, or clear your name to skip creating a login.")
        if pwd != pwd2:
            raise ValueError("The two passwords are not the same. Please type them again.")
        return name, pwd

    def on_start(self):
        try:
            login = self._validate_login()
            if self.backend_var.get() == 'sqlite':
                config.Config.DB_BACKEND = 'sqlite'
                db.reset()
                db.prepare()
            else:
                settings = self._mysql_settings()
                try:
                    state = self._mysql_state(settings)
                except Exception as e:
                    raise ValueError(f"Could not connect to the MySQL server:\n{e}")
                config.Config.DB_CONFIG.clear()
                config.Config.DB_CONFIG.update(settings)
                config.Config.DB_BACKEND = 'mysql'
                db.reset()
                if state == 'empty':
                    import setup_database
                    if not setup_database.create_database():
                        raise ValueError("The MySQL database could not be created. "
                                         "Check that this user may create databases.")
        except ValueError as e:
            messagebox.showwarning("Almost there", str(e), parent=self.win)
            return
        except Exception as e:
            config.Config.DB_BACKEND = None
            messagebox.showerror("Setup problem", f"The data storage could not be prepared:\n{e}", parent=self.win)
            return

        if login:
            # A password was asked for, so the program will require it from now on.
            config.Config.add_user(login[0], 'Administrator', login[1])  # first user: logged in
            config.Config.REQUIRE_LOGIN = True
        if not config.Config.save_user_settings():
            messagebox.showwarning("Settings", "Your choices could not be saved and will be asked again "
                                               "next time.", parent=self.win)
        self.completed = True
        self.win.destroy()

    def on_exit(self):
        self.completed = False
        self.win.destroy()

    def show(self) -> bool:
        self.parent.wait_window(self.win)
        return self.completed
