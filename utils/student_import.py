"""Import students from an Excel (.xlsx) or CSV file.

Two steps, so nothing is written before the user has seen what will happen:

    plan = plan_student_import(path, update_existing=False)   # read + check, no writes
    result = apply_student_import(plan)                       # save the accepted rows

Expected columns (header names are matched loosely, in any order):
    student_code, student_name, class, birth_date, parent_name,
    parent_phone, enrollment_date, status
Also understood: first_name + last_name instead of student_name, parent_email,
address, and common variations such as "Name", "Grade", "DOB", "Guardian".
"""
import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import config
from database.connection import db
from models.student import Student

# Canonical field -> accepted header spellings (compared after normalising).
COLUMN_ALIASES: Dict[str, tuple] = {
    "student_code": ("student_code", "code", "student_id", "admission_no", "admission_number", "reg_no"),
    "student_name": ("student_name", "name", "full_name", "student", "pupil_name", "learner_name"),
    "first_name": ("first_name", "firstname", "given_name", "first"),
    "last_name": ("last_name", "lastname", "surname", "family_name", "last"),
    "class": ("class", "class_name", "grade", "standard", "form", "level"),
    "birth_date": ("birth_date", "date_of_birth", "dob", "birthdate", "birthday"),
    "parent_name": ("parent_name", "parent", "guardian", "guardian_name", "parent_guardian"),
    "parent_phone": ("parent_phone", "phone", "phone_number", "parent_contact", "contact", "guardian_phone", "mobile"),
    "parent_email": ("parent_email", "email", "guardian_email"),
    "address": ("address", "home_address", "location"),
    "enrollment_date": ("enrollment_date", "enrolment_date", "admission_date", "date_enrolled", "date_joined"),
    "status": ("status", "active", "is_active"),
    "new_student": ("new_student", "is_new", "new"),
}
TEMPLATE_COLUMNS = ["student_code", "student_name", "class", "birth_date", "parent_name",
                    "parent_phone", "enrollment_date", "status"]

NEW, UPDATE, SKIP, ERROR = "New", "Update", "Skip", "Problem"


@dataclass
class ImportRow:
    row_number: int                 # spreadsheet row, for messages
    action: str                     # NEW / UPDATE / SKIP / ERROR
    message: str = ""
    student: Optional[Student] = None
    notes: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        if not self.student:
            return ""
        return f"{self.student.first_name} {self.student.last_name}".strip()


@dataclass
class ImportPlan:
    source: Path
    rows: List[ImportRow]
    update_existing: bool
    unknown_columns: List[str] = field(default_factory=list)

    def count(self, action: str) -> int:
        return sum(1 for r in self.rows if r.action == action)

    @property
    def to_save(self) -> List[ImportRow]:
        return [r for r in self.rows if r.action in (NEW, UPDATE)]


# --- reading -----------------------------------------------------------------

def _normalise_header(text) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text or "").strip().lower()).strip("_")


_ALIAS_LOOKUP = {alias: canonical for canonical, aliases in COLUMN_ALIASES.items() for alias in aliases}


def _read_raw_rows(path: Path) -> List[List]:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            return [list(row) for row in sheet.iter_rows(values_only=True)]
        finally:
            workbook.close()
    if suffix == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            return [row for row in csv.reader(handle, dialect)]
    if suffix == ".xls":
        raise ValueError("Old .xls files are not supported. In Excel choose File > Save As > "
                         "Excel Workbook (*.xlsx) and import that file instead.")
    raise ValueError("Choose an Excel workbook (.xlsx) or a CSV file.")


def _is_blank_or_separator(row) -> bool:
    texts = [str(c).strip() for c in row if c is not None and str(c).strip()]
    return not texts or all(re.fullmatch(r"[-=_ ]+", t) for t in texts)


def read_table(path) -> tuple:
    """Return (column map {canonical: index}, data rows [(row_number, values)], unknown headers)."""
    path = Path(path)
    raw = _read_raw_rows(path)
    for index, row in enumerate(raw[:15]):              # header may sit below a title
        mapping, unknown = {}, []
        for col, cell in enumerate(row):
            key = _ALIAS_LOOKUP.get(_normalise_header(cell))
            if key and key not in mapping:
                mapping[key] = col
            elif cell not in (None, ""):
                unknown.append(str(cell).strip())
        has_name = "student_name" in mapping or ("first_name" in mapping and "last_name" in mapping)
        if has_name and "class" in mapping:
            data = [(n + 1, r) for n, r in enumerate(raw[index + 1:], start=index + 1)
                    if not _is_blank_or_separator(r)]
            return mapping, data, unknown
    raise ValueError("No heading row was found. The sheet needs at least the columns "
                     "'student_name' (or first_name and last_name) and 'class'.")


# --- value parsing -------------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y",
                 "%d/%m/%y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y")


def parse_date(value) -> Optional[date]:
    """Excel dates, Excel serial numbers and common written formats (day first)."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and 1 < value < 100000:
        return date(1899, 12, 30) + timedelta(days=int(value))      # Excel serial date
    text = str(value).strip()
    if " " in text and re.match(r"\d{4}-\d{2}-\d{2} ", text):
        text = text.split(" ")[0]                                     # "2015-03-01 00:00:00"
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"'{value}' is not a date (use e.g. 2015-03-01 or 01/03/2015)")


def parse_phone(value) -> str:
    """Excel stores 0999123456 as the number 999123456; put the leading zero back."""
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    if isinstance(value, int) and len(text) == 9:
        text = "0" + text
    return text


def parse_status(value) -> bool:
    text = str(value if value is not None else "").strip().lower()
    if text in ("", "active", "yes", "y", "1", "true", "current", "enrolled"):
        return True
    if text in ("inactive", "no", "n", "0", "false", "left", "withdrawn", "graduated", "transferred"):
        return False
    raise ValueError(f"status '{value}' should be Active or Inactive")


def split_name(full_name: str) -> tuple:
    """'Chikondi Grace Banda' -> ('Chikondi Grace', 'Banda'): the last word is the surname."""
    parts = str(full_name or "").split()
    if len(parts) < 2:
        return " ".join(parts), ""
    return " ".join(parts[:-1]), parts[-1]


def _cell(values, mapping, key):
    index = mapping.get(key)
    if index is None or index >= len(values):
        return None
    value = values[index]
    return value.strip() if isinstance(value, str) else value


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


# --- planning ----------------------------------------------------------------

def _existing_students() -> tuple:
    rows = db.execute_query(
        "SELECT student_id, student_code, first_name, last_name, class, birth_date, is_active, is_new "
        "FROM students", fetch=True) or []
    by_code = {str(r["student_code"]).strip().upper(): r for r in rows if r.get("student_code")}
    by_name_class: Dict[tuple, list] = {}     # a name can belong to several records (e.g. old + new)
    for r in rows:
        key = (str(r["first_name"]).strip().lower(), str(r["last_name"]).strip().lower(),
               str(r["class"]).strip().lower())
        by_name_class.setdefault(key, []).append(r)
    return by_code, by_name_class


def _known_classes() -> Dict[str, str]:
    """lower-case name -> spelling already used, so 'grade 1' joins the existing 'Grade 1'."""
    names = {}
    for sql in ("SELECT class_name AS name FROM classes", "SELECT DISTINCT class AS name FROM students"):
        for r in db.execute_query(sql, fetch=True) or []:
            if r.get("name"):
                names.setdefault(str(r["name"]).strip().lower(), str(r["name"]).strip())
    return names


def plan_student_import(path, update_existing: bool = False) -> ImportPlan:
    """Read and check every row; nothing is written to the database."""
    mapping, data, unknown = read_table(path)
    by_code, by_name_class = _existing_students()
    classes = _known_classes()
    seen_codes, seen_names = {}, {}
    rows: List[ImportRow] = []

    for row_number, values in data:
        notes: List[str] = []
        try:
            if "student_name" in mapping:
                first, last = split_name(_text(_cell(values, mapping, "student_name")))
            else:
                first, last = (_text(_cell(values, mapping, "first_name")),
                               _text(_cell(values, mapping, "last_name")))
            if not first:
                raise ValueError("the student's name is empty")
            if not last:
                raise ValueError(f"'{first}' needs a surname (first and last name)")
            class_raw = _text(_cell(values, mapping, "class"))
            if not class_raw:
                raise ValueError("the class is empty")
            class_name = classes.get(class_raw.lower(), class_raw)

            code = _text(_cell(values, mapping, "student_code")).upper()
            birth = parse_date(_cell(values, mapping, "birth_date"))
            enrolled = parse_date(_cell(values, mapping, "enrollment_date"))
            if not enrolled:
                enrolled = date.today()
                notes.append("no enrollment date - today used")
            active = parse_status(_cell(values, mapping, "status"))
            new_flag = _cell(values, mapping, "new_student")
            is_new = parse_status(new_flag) if new_flag not in (None, "") else False

            student = Student(
                student_code=code, first_name=first, last_name=last, class_name=class_name,
                birth_date=birth, parent_name=_text(_cell(values, mapping, "parent_name")),
                parent_phone=parse_phone(_cell(values, mapping, "parent_phone")),
                parent_email=_text(_cell(values, mapping, "parent_email")),
                address=_text(_cell(values, mapping, "address")),
                enrollment_date=enrolled, is_active=active, is_new=is_new,
            )
            ok, problem = student.validate()
            if not ok:
                raise ValueError(problem)
        except ValueError as e:
            rows.append(ImportRow(row_number, ERROR, str(e)[:1].upper() + str(e)[1:]))
            continue

        name_key = (first.lower(), last.lower(), class_name.lower())
        if code and code in seen_codes:
            rows.append(ImportRow(row_number, ERROR, f"Code {code} is also used on row {seen_codes[code]}",
                                  student))
            continue
        # Same name and class twice in the file is a repeat unless both rows carry
        # different student codes (e.g. a pupil's old inactive record and the new one).
        earlier = seen_names.get(name_key)
        if earlier and not (code and earlier[1] and code != earlier[1]):
            rows.append(ImportRow(row_number, SKIP, f"Same student as row {earlier[0]}", student))
            continue
        if earlier and active and earlier[2]:
            rows.append(ImportRow(row_number, ERROR, f"Rows {earlier[0]} and {row_number} are two active "
                                  f"students called {first} {last} in {class_name}; mark one Inactive",
                                  student))
            continue
        if code:
            seen_codes[code] = row_number
        if not earlier or active:
            seen_names[name_key] = (row_number, code, active)

        candidates = by_name_class.get(name_key, [])
        if code:
            # A student code identifies the record; an unknown code is a new record.
            existing = by_code.get(code)
            clash = next((c for c in candidates if c.get("is_active")), None) if existing is None else None
            if clash and active:
                rows.append(ImportRow(row_number, ERROR,
                                      f"An active {first} {last} in {class_name} already exists as "
                                      f"{clash['student_code']}. Use that code to update them, or mark "
                                      f"this row Inactive.", student))
                continue
        else:
            # Without a code, the name and class identify the student.
            existing = next((c for c in candidates if c.get("is_active")), candidates[0] if candidates else None)
        if existing is not None:
            if not update_existing:
                rows.append(ImportRow(row_number, SKIP,
                                      f"Already in the system as {existing['student_code']}", student, notes))
                continue
            student.student_id = existing["student_id"]
            student.student_code = student.student_code or existing["student_code"]
            if new_flag in (None, ""):
                student.is_new = bool(existing.get("is_new"))   # keep fee status unless the sheet says
            rows.append(ImportRow(row_number, UPDATE, f"Updates {student.student_code}", student, notes))
        else:
            if code and not code.startswith("STU"):
                rows.append(ImportRow(row_number, ERROR, "Student code must start with STU", student))
                continue
            rows.append(ImportRow(row_number, NEW, "; ".join(notes) or "Will be added", student, notes))

    known_names = {a for aliases in COLUMN_ALIASES.values() for a in aliases}
    ignored = [u for u in unknown if _normalise_header(u) not in known_names]
    return ImportPlan(Path(path), rows, update_existing, ignored)


# --- applying ----------------------------------------------------------------

def _ensure_class(class_name: str) -> None:
    """Make the class selectable in the Add Student form (which lists the classes table)."""
    found = db.execute_query("SELECT class_id FROM classes WHERE LOWER(class_name) = LOWER(%s)",
                             (class_name,), fetch=True)
    if not found:
        db.execute_query("INSERT INTO classes (class_name, academic_year) VALUES (%s, %s)",
                         (class_name, config.Config.CURRENT_ACADEMIC_YEAR))


def apply_student_import(plan: ImportPlan) -> Dict[str, object]:
    """Save every New/Update row. Returns counts and any rows that failed to save."""
    added = updated = 0
    failed: List[str] = []
    for row in plan.to_save:
        try:
            _ensure_class(row.student.class_name)
            ok, message = row.student.save()
        except Exception as e:     # keep going; report the row
            ok, message = False, str(e)
        if ok:
            if row.action == NEW:
                added += 1
            else:
                updated += 1
        else:
            failed.append(f"Row {row.row_number} ({row.name}): {message}")
    return {"added": added, "updated": updated, "failed": failed}


def write_template(path) -> Path:
    """Create an empty workbook with the expected columns and one example row."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Students"
    sheet.append(TEMPLATE_COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.append(["", "Chikondi Banda", "Std 1", date(2018, 3, 14), "Grace Banda",
                  "0999123456", date.today(), "Active"])
    for column, width in zip("ABCDEFGH", (14, 26, 10, 13, 24, 15, 16, 10)):
        sheet.column_dimensions[column].width = width
    for row in sheet.iter_rows(min_row=2, max_row=2):
        row[3].number_format = row[6].number_format = "yyyy-mm-dd"
        row[5].number_format = "@"          # keep the leading zero of phone numbers
    notes = workbook.create_sheet("How to fill in")
    for line in (
        "One student per row on the 'Students' sheet. Delete the example row.",
        "student_code: leave empty to have one created (STU....).",
        "student_name: first name(s) then surname, e.g. Chikondi Grace Banda.",
        "birth_date, enrollment_date: dates such as 2018-03-14 or 14/03/2018.",
        "status: Active or Inactive (empty means Active).",
        "Students already in the program are skipped unless you tick 'Update students that already exist'.",
    ):
        notes.append([line])
    notes.column_dimensions["A"].width = 100
    path = Path(path)
    workbook.save(path)
    return path
