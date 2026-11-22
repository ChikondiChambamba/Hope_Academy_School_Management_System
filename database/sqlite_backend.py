"""SQLite storage: one file on this computer, nothing to install.

The application's SQL is written in MySQL dialect. This backend runs it
unchanged by translating the few syntactic differences and providing the MySQL
functions the queries use (CONCAT, YEAR, MONTH, CURDATE, NOW, DATE_FORMAT).
Constructs that cannot be translated mechanically are written per dialect at
the call site, using `db.dialect` / `db.group_concat_distinct`.
"""
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .session_state import SessionState

def _schema_file() -> Path:
    """schema_sqlite.sql in the source tree, or in the bundle of a packaged build."""
    import config
    bundled = Path(config.Config.RESOURCE_DIR) / "database" / "schema_sqlite.sql"
    return bundled if bundled.exists() else Path(__file__).resolve().parent / "schema_sqlite.sql"

# Bump when schema_sqlite.sql changes and add the upgrade step to _MIGRATIONS.
SCHEMA_VERSION = 1
_MIGRATIONS: Dict[int, str] = {}  # {version: "SQL script upgrading version-1 -> version"}


# --- value conversion --------------------------------------------------------

def _adapt_datetime(value: datetime) -> str:
    return value.isoformat(sep=" ", timespec="seconds")


sqlite3.register_adapter(date, lambda v: v.isoformat())
sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_adapter(time, lambda v: v.isoformat(timespec="seconds"))
sqlite3.register_adapter(Decimal, float)
sqlite3.register_adapter(bool, int)


def _to_date(raw: bytes):
    text = raw.decode()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return text


def _to_datetime(raw: bytes):
    text = raw.decode()
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.combine(date.fromisoformat(text[:10]), time())
        except ValueError:
            return text


# Declared column types -> Python values, matching what mysql-connector returns.
sqlite3.register_converter("DATE", _to_date)
sqlite3.register_converter("DATETIME", _to_datetime)
sqlite3.register_converter("TIMESTAMP", _to_datetime)


# --- MySQL functions used by the application's SQL ---------------------------

def _concat(*parts):
    # MySQL semantics: NULL if any argument is NULL.
    if any(p is None for p in parts):
        return None
    return "".join(str(int(p)) if isinstance(p, float) and p.is_integer() else str(p) for p in parts)


def _date_part(value, start, end):
    if value is None:
        return None
    try:
        return int(str(value)[start:end])
    except ValueError:
        return None


_MYSQL_TO_STRFTIME = {
    "%Y": "%Y", "%y": "%y", "%m": "%m", "%c": "%-m", "%d": "%d", "%e": "%-d",
    "%H": "%H", "%i": "%M", "%s": "%S", "%S": "%S", "%M": "%B", "%b": "%b",
    "%W": "%A", "%a": "%a", "%p": "%p", "%%": "%%",
}


def _date_format(value, fmt):
    if value is None or fmt is None:
        return None
    text = str(value)
    try:
        moment = datetime.fromisoformat(text) if len(text) > 10 else datetime.combine(date.fromisoformat(text), time())
    except ValueError:
        return None
    out = []
    i = 0
    while i < len(fmt):
        token = fmt[i:i + 2]
        if token in _MYSQL_TO_STRFTIME:
            code = _MYSQL_TO_STRFTIME[token]
            if code == "%-m":
                out.append(str(moment.month))
            elif code == "%-d":
                out.append(str(moment.day))
            else:
                out.append(moment.strftime(code))
            i += 2
        else:
            out.append(fmt[i])
            i += 1
    return "".join(out)


class _GroupConcatSorted:
    """GROUP_CONCAT(DISTINCT x ORDER BY x SEPARATOR sep) for SQLite."""

    def __init__(self):
        self.values = set()
        self.sep = ","

    def step(self, value, sep):
        if value is not None:
            self.values.add(str(value))
        if sep is not None:
            self.sep = sep

    def finalize(self):
        if not self.values:
            return None
        key = (lambda v: (0, int(v), "") if v.lstrip("-").isdigit() else (1, 0, v))
        return self.sep.join(sorted(self.values, key=key))


# --- SQL translation ---------------------------------------------------------

_INSERT_IGNORE = re.compile(r"\bINSERT\s+IGNORE\b", re.IGNORECASE)
_IS_INSERT = re.compile(r"\s*(INSERT|REPLACE)\b", re.IGNORECASE)


@lru_cache(maxsize=2048)
def translate(sql: str) -> str:
    """MySQL-flavoured SQL -> SQLite (placeholders, INSERT IGNORE)."""
    sql = _INSERT_IGNORE.sub("INSERT OR IGNORE", sql)
    sql = sql.replace("%%", "\0").replace("%s", "?").replace("\0", "%")
    return sql


def _dict_rows(cursor, row):
    return {col[0]: value for col, value in zip(cursor.description, row)}


class SQLiteBackend(SessionState):
    dialect = "sqlite"
    is_sqlite = True
    # The bundled schema is always complete, so runtime CREATE/ALTER is skipped.
    manages_schema = True

    @property
    def backend(self):
        """Lets a backend stand in for the `db` facade (used by tests and tools)."""
        return self

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._tx_depth = 0
        self._init_session_state()

    # connection lifecycle
    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self.path),
                detect_types=sqlite3.PARSE_DECLTYPES,
                isolation_level=None,          # autocommit; transactions are explicit
                check_same_thread=False,
            )
            conn.row_factory = _dict_rows
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.create_function("CONCAT", -1, _concat, deterministic=True)
            conn.create_function("YEAR", 1, lambda v: _date_part(v, 0, 4), deterministic=True)
            conn.create_function("MONTH", 1, lambda v: _date_part(v, 5, 7), deterministic=True)
            conn.create_function("DAY", 1, lambda v: _date_part(v, 8, 10), deterministic=True)
            conn.create_function("CURDATE", 0, lambda: date.today().isoformat())
            conn.create_function("NOW", 0, lambda: _adapt_datetime(datetime.now()))
            conn.create_function("DATE_FORMAT", 2, _date_format, deterministic=True)
            conn.create_aggregate("GROUP_CONCAT_SORTED", 2, _GroupConcatSorted)
            self._conn = conn
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None
            self._reset_session_state()

    reset = reset_pool = close

    def test_connection(self) -> bool:
        try:
            with self._lock:
                self._connect().execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

    # schema
    def prepare(self) -> None:
        """Create the database on first use, or upgrade an older file."""
        with self._lock:
            conn = self._connect()
            version = conn.execute("PRAGMA user_version").fetchone()["user_version"]
            has_tables = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'students'"
            ).fetchone()
            self._mark_write()
            if not has_tables:
                conn.executescript(_schema_file().read_text(encoding="utf-8"))
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                return
            for target in range(max(version, 1) + 1, SCHEMA_VERSION + 1):
                conn.executescript(_MIGRATIONS[target])
                conn.execute(f"PRAGMA user_version = {target}")
            if version < 1:
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def table_exists(self, table: str) -> bool:
        rows = self.execute_query("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = %s", (table,), fetch=True)
        return bool(rows)

    def list_tables(self) -> List[str]:
        rows = self.execute_query(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%%' ORDER BY name",
            fetch=True)
        return [r["name"] for r in rows]

    def column_exists(self, table: str, column: str) -> bool:
        if not re.fullmatch(r"\w+", table):
            raise ValueError(f"invalid table name {table!r}")
        rows = self.execute_query(f"PRAGMA table_info({table})", fetch=True)
        return any(r["name"] == column for r in rows)

    @staticmethod
    def group_concat_distinct(expr: str, separator_literal: str) -> str:
        return f"GROUP_CONCAT_SORTED({expr}, {separator_literal})"


    @staticmethod
    def upsert_clause(conflict_columns, set_new=(), set_sql=None) -> str:
        """Clause appended to an INSERT to update the existing row on a key conflict.

        set_new: columns that take the value the INSERT tried to write.
        set_sql: {column: SQL expression}, evaluated against the existing row.
        """
        parts = [f"{c} = excluded.{c}" for c in set_new]
        parts += [f"{c} = {expr}" for c, expr in (set_sql or {}).items()]
        return f"ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET " + ", ".join(parts)

    # queries
    def execute_query(self, query: str, params: Sequence = None, fetch: bool = False):
        with self._lock:
            conn = self._connect()
            changes_before = conn.total_changes
            cursor = conn.execute(translate(query), tuple(params or ()))
            try:
                if fetch:
                    return cursor.fetchall()
                changed = conn.total_changes != changes_before
                if changed:
                    self._mark_write()
                # Like mysql-connector: the new row id after an INSERT, otherwise 0
                # (sqlite3 would report the previous insert's id for an ignored row).
                return (cursor.lastrowid or 0) if changed and _IS_INSERT.match(query) else 0
            finally:
                cursor.close()

    def execute_many(self, query: str, params_list: List[Sequence]) -> None:
        with self._lock:
            conn = self._connect()
            self._mark_write()
            if self._tx_depth:
                conn.executemany(translate(query), [tuple(p) for p in params_list])
                return
            conn.execute("BEGIN")
            try:
                conn.executemany(translate(query), [tuple(p) for p in params_list])
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    @contextmanager
    def transaction(self):
        """All statements inside run atomically; any exception rolls everything back."""
        with self._lock:
            conn = self._connect()
            outermost = self._tx_depth == 0
            if outermost:
                conn.execute("BEGIN IMMEDIATE")
            self._tx_depth += 1
            try:
                yield self
            except BaseException:
                self._tx_depth -= 1
                if outermost:
                    conn.execute("ROLLBACK")
                    self._mark_write()   # cached results may include rolled-back rows
                raise
            else:
                self._tx_depth -= 1
                if outermost:
                    conn.execute("COMMIT")

    def execute_query_in_transaction(self, connection, query: str, params: Sequence = None, fetch: bool = False):
        return self.execute_query(query, params, fetch=fetch)

    # file operations used by backup / restore
    def backup_to(self, target_path) -> None:
        """Write a consistent copy of the database file (safe while the app is running)."""
        with self._lock:
            target = sqlite3.connect(str(target_path))
            try:
                self._connect().backup(target)
            finally:
                target.close()

    def integrity_ok(self) -> bool:
        with self._lock:
            row = self._connect().execute("PRAGMA integrity_check").fetchone()
            return list(row.values())[0] == "ok"

    def optimize(self) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute("ANALYZE")
            conn.execute("VACUUM")


def is_school_database(path) -> bool:
    """True if `path` is an SQLite file created by this application."""
    try:
        conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
        try:
            return conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'students'"
            ).fetchone() is not None
        finally:
            conn.close()
    except sqlite3.Error:
        return False
