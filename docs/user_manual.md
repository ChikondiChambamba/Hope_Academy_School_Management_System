Hope Academy School Management System - User Manual

Overview

This manual explains how to install and use the Hope Academy School Management System on a Windows computer: students, teachers, fees, expenses, inventory, attendance and reports.


Installing the program
----------------------
1. Run Hope_Academy_School_Management_System_Setup.exe and follow the steps. Nothing else needs to be installed.
2. Open the program from the desktop or the Start menu.

The first time it opens, a Welcome window asks two questions:

1. Where should the school's information be saved?
   Choose "On this computer (recommended)". Everything is kept in one file on this computer.
   (The MySQL option is only for schools where someone has already set up a MySQL server.)
2. Protect the program with a login (optional).
   If other people use this computer, type your name and a password. You will need them every
   time you open the program, so keep the password somewhere safe. Leave the fields empty to skip;
   a login can be added later under Edit > Manage Users.

Press Start. The Welcome window is not shown again.


Importing students from Excel
-----------------------------
Students tab > Import from Excel (or File > Import Students from Excel).

1. Press "Save an empty template..." the first time, or use an existing list. The columns are:
   student_code, student_name, class, birth_date, parent_name, parent_phone, enrollment_date, status.
   A Student List exported from the Reports tab can be imported as it is.
2. Press "Choose Excel file..." and pick the workbook (.xlsx) or a .csv file.
3. Check the list. Every row says what will happen:
   - New: will be added. Leave student_code empty and a code is created.
   - Update / Skip: the student is already in the program (same code, or same name and class).
     Tick "Update students that already exist" to overwrite their details from the sheet.
   - Problem (red): will not be imported; the reason is shown, e.g. a missing surname or a wrong date.
4. Press Import. Fix any red rows in Excel and import the file again; students already added are skipped.

Dates may be typed as 2018-03-14 or 14/03/2018 (day first). Phone numbers that lost their leading 0 in
Excel are corrected. Status is Active or Inactive (empty means Active).


Logging in and out
------------------
- If a login was created, the program asks for it when it opens (File > Login, Ctrl+I).
- File > Logout (Ctrl+L) closes your session; nobody can see the records until someone logs in.
- Each person can have their own login and role (Administrator, Headteacher, Finance, Inventory).
  Only an Administrator can manage users, change preferences, or back up and restore data.


Where your data is kept, and backups
------------------------------------
- Edit > Preferences > Data Storage shows where the data file is, with a button to open the folder.
- A backup copy is made automatically once a day when the program starts; the last 14 are kept in the
  backups folder shown there.
- File > Backup Database makes an extra copy at any time. Copy it to a USB stick or cloud storage
  now and then, in case the computer is lost or damaged.
- File > Restore Database puts a backup back. Your current data is saved first, so a restore can be
  undone by restoring that copy.
- Uninstalling the program does not delete the data; reinstalling picks it up again.
- Tools > Database Maintenance checks the data file for damage and tidies it. It never deletes records.

Developers: see docs/DEVELOPER_GUIDE.md for running from source, tests and building the installer.

User Interface Guide
--------------------
Main tabs
- Dashboard: Quick metrics and shortcuts
- Students: Add/edit students, view balances, and payment history
- Teachers: Manage teacher profiles, salaries, and advances
- Finance: Record payments, expenses, and manage fee types
- Inventory: Track stock and items
- Attendance: Record class attendance
- Reports: Generate student lists, fee reports, and financial summaries

Students
--------
- Add Student: Fill required fields — first name, last name, class, parent/guardian, phone, enrollment date. Set `is_new` to True for newly enrolled students.
- Edit Student: Update contact and academic details. `teacher_code` and other stable identifiers are preserved on edit.
- Deactivate/Delete: Use caution — deactivation keeps history, deletion removes the record.

Teachers
--------
- Teacher records include `salary_amount` (monthly salary).
- Salary advances: Record advances using the Finance/Salary workflow. Advances are stored in `teacher_salary_advances` and can be tracked / deducted later.

Finance
-------
Fee types
- Fee types are defined per academic year. Only fee types matching `config.Config.CURRENT_ACADEMIC_YEAR` are shown in fee selection UIs.
- If you cannot see fee types, check the `academic_year` column on `fee_types` and update it to match `CURRENT_ACADEMIC_YEAR`.

Recording payments
- Open Finance → Record Fee Payment or use the student's profile to record payments.
- When recording payment, you can search/select a student by ID or type their name. If you type a name, the system performs a fallback lookup in the database.
- Leave Receipt Number blank to auto-generate. Receipts use the format: `REC-YYYYMMDD-XXXX`.

Receipt generation and uniqueness
- Receipts are created using a DB-backed per-day sequence (`receipt_sequence`) to avoid duplicate receipt numbers during concurrent inserts.
- If you see a MySQL 1062 duplicate error, check that `receipt_sequence` exists and the application has insert/update permission.

Business rules enforced by the app
- Registration & Uniform fees only apply to students with `is_new = True`.
- Tuition mapping by class: the UI/code applies tuition amounts based on the student's class (e.g., Nursery/Reception vs Grades 1–7). These are applied at runtime; fee_type rows keep historical values.
- When a tuition payment is recorded for a student, other tuition fee types for that student are recorded as exemptions in `student_fee_exemptions` to prevent duplicate tuition charges.

Student balances
- Balances are computed per-student using only the fee types that apply to them (honoring `student_fee_exemptions` and `is_new`). Reports and the Student tab now use conditional aggregation queries so totals reflect applicable fees only.

Expenses
- Record general expenses from the Finance tab.
- Expenses appear in financial summary reports and reduce the net collection for the selected period.

Reports
-------
- Student Fees Report: Shows per-student expected amount, paid, and balance — respects exemptions and `is_new`.
- Fee Collection Report: Lists individual payments with dates, payers, and receipts for a date range.
- Expense Report: Lists recorded expenses between dates.
- Financial Summary: Aggregates total collections and expenses by academic year or term.

PDF reports are saved in the "reports" folder next to the data file (Edit > Preferences > Open data folder).

Database & Developer Notes
-------------------------
Key tables
- `students` — student profile and flags (`is_new`)
- `fee_types` — fee definitions, includes `academic_year` to scope fee types
- `student_fees` — recorded fee payments, includes `receipt_number`
- `receipt_sequence` — stores per-date sequence and prevents race conditions on receipts
- `student_fee_exemptions` — per-student exemptions for specific fee types
- `teachers`, `teacher_salary_advances` — teacher payroll and advances

Important queries
- The codebase centralizes SQL in `database/queries.py`. Student fee totals are computed using conditional `SUM(CASE WHEN ... THEN amount ELSE 0 END)` aggregations and LEFT JOINs to `student_fee_exemptions` so only applicable fees are summed.

Applying schema changes
- The repository includes `database/schema.sql`. Use `setup_database.py` or your preferred SQL client to apply schema migrations.
- A helper script `apply_db_changes.py` may exist to apply the latest small edits (like adding `salary_amount` or creating `teacher_salary_advances`). Run it from the project root.

Troubleshooting
---------------
Common issues
- Fee types not visible
  - Cause: `fee_types.academic_year` doesn't match `config.Config.CURRENT_ACADEMIC_YEAR`.
  - Fix: Update the `academic_year` value in DB or update `config.py` to the correct academic year.

- Duplicate receipt error (MySQL 1062)
  - Cause: simultaneous inserts generated the same receipt number or `receipt_sequence` is missing/inaccessible.
  - Fix: Verify `receipt_sequence` exists and has a PRIMARY KEY on `seq_date`. Ensure the DB user has INSERT and UPDATE privileges on it. If necessary, inspect the conflicting `student_fees` row and remove or reconcile it.

- UI error referencing `amount_entry` or similar widget
  - Cause: Running an older instance of the app after code changes.
  - Fix: Restart the application so updated modules are loaded.

- Incorrect student balances in reports
  - Cause: Older query logic (cross-join) computed totals against all fee types.
  - Fix: Upgrade to the current code which uses conditional aggregation; regenerate the report after restarting the app.

Testing
-------
Run unit tests (if included):

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

If you want to run quick manual checks:
1. Restart the app.
2. Add a new student and set `is_new = True`.
3. Record a registration payment; confirm registration/uniform apply only to `is_new` students.
4. Record tuition for a student and confirm other tuition fee types are recorded as exemptions automatically.
5. Generate Student Fees Report and confirm the expected vs paid vs balance values.

Support & Feedback
------------------
When reporting bugs, include:
- Steps to reproduce
- Screenshots of the UI and any error messages
- The content of the console output or traceback
- A SQL snippet or row that demonstrates unexpected DB state (if applicable)

If you'd like, I can also:
- Produce a printable PDF of this manual
- Add step-by-step screenshot guides for each major flow
- Create quick test scripts to validate finance flows

End of manual.
