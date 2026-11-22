"""Copy a MySQL school database into a new SQLite data file."""
from datetime import timedelta
from pathlib import Path
from typing import Dict

from .sqlite_backend import SQLiteBackend

# Tables that only link two other records; a link to a deleted record is meaningless.
LINK_TABLES = {"fee_type_classes", "student_classes", "student_fee_exemptions"}


def _sqlite_value(value):
    # mysql-connector returns TIME columns as timedelta.
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def copy_mysql_to_sqlite(mysql_backend, sqlite_path) -> Dict[str, int]:
    """Copy every table's rows (ids preserved). Returns {table: rows copied}.

    The target file must not exist yet. Row counts are verified afterwards.
    """
    target = Path(sqlite_path)
    if target.exists():
        raise FileExistsError(f"{target} already exists; choose a new file name.")
    lite = SQLiteBackend(target)
    lite.prepare()
    conn = lite._connect()
    copied: Dict[str, int] = {}
    source_tables = set(mysql_backend.list_tables())
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")
        for table in lite.list_tables():
            if table == "sqlite_sequence" or table not in source_tables:
                continue
            # hidden = 2/3 marks generated columns, which SQLite computes itself
            columns = [c["name"] for c in conn.execute(f"PRAGMA table_xinfo({table})").fetchall()
                       if c["hidden"] == 0]
            rows = mysql_backend.execute_query(f"SELECT * FROM `{table}`", fetch=True) or []
            if rows:
                shared = [c for c in columns if c in rows[0]]
                placeholders = ", ".join("?" for _ in shared)
                conn.executemany(
                    f"INSERT INTO {table} ({', '.join(shared)}) VALUES ({placeholders})",
                    [tuple(_sqlite_value(row[c]) for c in shared) for row in rows],
                )
            copied[table] = len(rows)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        lite.close()
        target.unlink(missing_ok=True)
        raise
    finally:
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass

    for table, expected in copied.items():
        actual = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        if actual != expected:
            lite.close()
            raise RuntimeError(f"{table}: copied {actual} of {expected} rows")

    # MySQL tables created without foreign keys can hold links to deleted rows.
    # Stale links in pure mapping tables mean nothing and are dropped; a broken
    # reference anywhere else (e.g. a payment) stops the copy for a human to look at.
    problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    unexpected = [p for p in problems if p["table"] not in LINK_TABLES]
    if unexpected:
        lite.close()
        target.unlink(missing_ok=True)
        raise RuntimeError(f"The MySQL data has {len(unexpected)} records pointing to missing rows, "
                           f"e.g. {dict(unexpected[0])}. Nothing was copied.")
    dropped: Dict[str, int] = {}
    for p in problems:
        conn.execute(f"DELETE FROM {p['table']} WHERE rowid = ?", (p["rowid"],))
        dropped[p["table"]] = dropped.get(p["table"], 0) + 1
    for table, n in dropped.items():
        copied[table] -= n
    copied["_stale_links_dropped"] = sum(dropped.values())
    lite.close()
    return copied
