"""Import students from Excel: choose a file, check the preview, then import."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import config
from utils.student_import import (ERROR, NEW, SKIP, UPDATE, apply_student_import,
                                  plan_student_import, write_template)

ROW_COLOURS = {NEW: '#e8f5e9', UPDATE: '#e3f2fd', SKIP: '#f5f5f5', ERROR: '#ffebee'}


class StudentImportDialog:
    def __init__(self, parent, on_imported=None):
        self.parent = parent
        self.on_imported = on_imported
        self.plan = None
        self.win = tk.Toplevel(parent)
        self.win.title("Import Students from Excel")
        self.win.geometry("900x560")
        self.win.minsize(760, 420)
        self.win.transient(parent)
        self._build()
        self.win.grab_set()

    def _build(self):
        body = ttk.Frame(self.win, padding=12)
        body.pack(fill='both', expand=True)

        ttk.Label(body, text="Import students from an Excel sheet", font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(body, foreground='#555', text=(
            "Columns: student_code, student_name, class, birth_date, parent_name, parent_phone, "
            "enrollment_date, status.\nNothing is saved until you have checked the list below and pressed Import."
        )).pack(anchor='w', pady=(2, 10))

        top = ttk.Frame(body)
        top.pack(fill='x')
        ttk.Button(top, text="Choose Excel file...", command=self.choose_file).pack(side='left')
        ttk.Button(top, text="Save an empty template...", command=self.save_template).pack(side='left', padx=8)
        self.update_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Update students that already exist", variable=self.update_var,
                        command=self.rebuild_plan).pack(side='left', padx=12)
        self.file_var = tk.StringVar(value="No file chosen")
        ttk.Label(body, textvariable=self.file_var, foreground='#333').pack(anchor='w', pady=(8, 4))

        table = ttk.Frame(body)
        table.pack(fill='both', expand=True)
        columns = ('row', 'action', 'code', 'name', 'class', 'details')
        self.tree = ttk.Treeview(table, columns=columns, show='headings')
        for col, title, width in (('row', 'Row', 50), ('action', 'Result', 80), ('code', 'Code', 90),
                                  ('name', 'Name', 200), ('class', 'Class', 90), ('details', 'Details', 340)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, stretch=(col == 'details'))
        for action, colour in ROW_COLOURS.items():
            self.tree.tag_configure(action, background=colour)
        scroll = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        bottom = ttk.Frame(body)
        bottom.pack(fill='x', pady=(10, 0))
        self.summary_var = tk.StringVar(value="Choose a file to see what will be imported.")
        ttk.Label(bottom, textvariable=self.summary_var).pack(side='left')
        ttk.Button(bottom, text="Close", command=self.win.destroy).pack(side='right')
        self.import_button = ttk.Button(bottom, text="Import", command=self.do_import, state='disabled')
        self.import_button.pack(side='right', padx=8)

    # actions
    def save_template(self):
        target = filedialog.asksaveasfilename(
            parent=self.win, title="Save template", defaultextension=".xlsx",
            initialfile="students_import_template.xlsx", filetypes=[("Excel workbook", "*.xlsx")])
        if not target:
            return
        try:
            write_template(target)
        except Exception as e:
            messagebox.showerror("Template", f"The template could not be saved:\n{e}", parent=self.win)
            return
        messagebox.showinfo("Template", f"Template saved to:\n{target}\n\nFill it in, then choose it here.",
                            parent=self.win)

    def choose_file(self):
        path = filedialog.askopenfilename(
            parent=self.win, title="Choose the student list",
            filetypes=[("Excel or CSV", "*.xlsx *.xlsm *.csv"), ("All files", "*.*")],
            initialdir=str(config.Config.PATHS.get('exports', Path.home())))
        if path:
            self.file_var.set(path)
            self.rebuild_plan()

    def rebuild_plan(self):
        path = self.file_var.get()
        if not path or path == "No file chosen":
            return
        self.win.config(cursor='watch')
        self.win.update_idletasks()
        try:
            self.plan = plan_student_import(path, update_existing=self.update_var.get())
        except Exception as e:
            self.plan = None
            self.tree.delete(*self.tree.get_children())
            self.summary_var.set("")
            self.import_button.configure(state='disabled')
            messagebox.showerror("Cannot read the file", str(e), parent=self.win)
            return
        finally:
            self.win.config(cursor='')
        self._show_plan()

    def _show_plan(self):
        self.tree.delete(*self.tree.get_children())
        order = {ERROR: 0, NEW: 1, UPDATE: 2, SKIP: 3}
        for row in sorted(self.plan.rows, key=lambda r: (order[r.action], r.row_number)):
            student = row.student
            self.tree.insert('', 'end', tags=(row.action,), values=(
                row.row_number, row.action,
                (student.student_code or 'new') if student else '',
                row.name, student.class_name if student else '', row.message))
        p = self.plan
        summary = (f"{p.count(NEW)} new, {p.count(UPDATE)} to update, {p.count(SKIP)} skipped, "
                   f"{p.count(ERROR)} with problems")
        if p.unknown_columns:
            summary += f"   (ignored columns: {', '.join(p.unknown_columns)})"
        self.summary_var.set(summary)
        count = len(p.to_save)
        self.import_button.configure(state='normal' if count else 'disabled',
                                     text=f"Import {count} student{'s' if count != 1 else ''}")

    def do_import(self):
        if not self.plan or not self.plan.to_save:
            return
        problems = self.plan.count(ERROR)
        if problems and not messagebox.askyesno(
                "Rows with problems",
                f"{problems} row(s) have problems and will NOT be imported (shown in red).\n\n"
                f"Import the other {len(self.plan.to_save)} now?", parent=self.win):
            return
        self.win.config(cursor='watch')
        self.win.update_idletasks()
        try:
            result = apply_student_import(self.plan)
        finally:
            self.win.config(cursor='')
        text = f"Added {result['added']} student(s), updated {result['updated']}."
        if result['failed']:
            text += "\n\nCould not save:\n" + "\n".join(result['failed'][:15])
            if len(result['failed']) > 15:
                text += f"\n... and {len(result['failed']) - 15} more"
        (messagebox.showwarning if result['failed'] else messagebox.showinfo)("Import finished", text,
                                                                           parent=self.win)
        if self.on_imported:
            self.on_imported()
        self.rebuild_plan()      # rows just imported now show as already existing
