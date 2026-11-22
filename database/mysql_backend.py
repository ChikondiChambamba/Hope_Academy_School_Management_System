"""MySQL storage (optional, for schools that run their own MySQL server)."""
import re
from contextlib import contextmanager
from typing import Dict, List, Optional, Sequence

import mysql.connector
from mysql.connector import Error, pooling

import config

from .session_state import SessionState


class MySQLBackend(SessionState):
    dialect = "mysql"
    is_sqlite = False
    # Older MySQL databases may predate some tables/columns; the app's
    # CREATE TABLE IF NOT EXISTS / ADD COLUMN checks keep them up to date.
    manages_schema = False

    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self._pool = None
        self._init_session_state()

    def _initialize_pool(self) -> None:
        try:
            # pool_reset_session=False: the app keeps no per-session state (transaction()
            # restores autocommit itself), and the reset costs a server round-trip per query.
            self._pool = pooling.MySQLConnectionPool(
                # One user: a transaction plus one lookup inside it is the most needed at once.
                pool_name="school_pool", pool_size=2, pool_reset_session=False, **self.db_config)
            config.Config._write_config_log(
                f"MySQL pool created for {self.db_config.get('user')}@{self.db_config.get('host')}/"
                f"{self.db_config.get('database')}"
            )
        except Error as e:
            self._pool = None
            config.Config._write_config_log(f"MySQL pool initialization failed: {e}", level="ERROR")

    def get_connection(self):
        if self._pool is None:
            self._initialize_pool()
        if self._pool:
            return self._pool.get_connection()
        return mysql.connector.connect(**self.db_config)

    def close(self) -> None:
        pool, self._pool = self._pool, None
        if pool is not None:
            try:
                pool._remove_connections()  # MySQLConnectionPool has no public close API
            except Exception:
                pass
        self._reset_session_state()

    reset = reset_pool = close

    @property
    def backend(self):
        """Lets a backend stand in for the `db` facade (used by tests and tools)."""
        return self

    def test_connection(self) -> bool:
        try:
            self.get_connection().close()
            return True
        except Error:
            return False

    def prepare(self) -> None:
        """MySQL databases are created with setup_database.py / apply_db_changes.py."""

    # schema inspection
    def table_exists(self, table: str) -> bool:
        rows = self.execute_query(
            "SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
            (table,), fetch=True)
        return bool(rows)

    def list_tables(self) -> List[str]:
        rows = self.execute_query(
            "SELECT TABLE_NAME AS name FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME",
            fetch=True)
        return [r["name"] for r in rows]

    def column_exists(self, table: str, column: str) -> bool:
        rows = self.execute_query(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (table, column), fetch=True)
        return bool(rows)

    @staticmethod
    def group_concat_distinct(expr: str, separator_literal: str) -> str:
        return f"GROUP_CONCAT(DISTINCT {expr} ORDER BY {expr} SEPARATOR {separator_literal})"


    @staticmethod
    def upsert_clause(conflict_columns, set_new=(), set_sql=None) -> str:
        """Clause appended to an INSERT to update the existing row on a key conflict.

        set_new: columns that take the value the INSERT tried to write.
        set_sql: {column: SQL expression}, evaluated against the existing row.
        """
        parts = [f"{c} = VALUES({c})" for c in set_new]
        parts += [f"{c} = {expr}" for c, expr in (set_sql or {}).items()]
        return "ON DUPLICATE KEY UPDATE " + ", ".join(parts)

    # queries
    def execute_query(self, query: str, params: Sequence = None, fetch: bool = False):
        connection = cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, tuple(params or ()))
            if fetch:
                return cursor.fetchall()
            connection.commit()
            if cursor.rowcount != 0:      # -1 (unknown) counts as a change
                self._mark_write()
            return cursor.lastrowid
        except Error:
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def execute_many(self, query: str, params_list: List[Sequence]) -> None:
        connection = cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.executemany(query, params_list)
            connection.commit()
            self._mark_write()
        except Error:
            if connection:
                connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    @contextmanager
    def transaction(self):
        """All statements inside run atomically; any exception rolls everything back."""
        connection = self.get_connection()
        try:
            connection.autocommit = False
            yield connection
            connection.commit()
            self._mark_write()
        except BaseException:
            try:
                connection.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                connection.autocommit = True
            except Exception:
                pass
            connection.close()

    def execute_query_in_transaction(self, connection, query: str, params: Sequence = None, fetch: bool = False):
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, tuple(params or ()))
            return cursor.fetchall() if fetch else cursor.lastrowid
        finally:
            cursor.close()

    # maintenance
    def integrity_ok(self) -> bool:
        tables = self.list_tables()
        if not tables:
            return True
        for table in tables:
            if not re.fullmatch(r"\w+", table):
                continue
            rows = self.execute_query(f"CHECK TABLE `{table}`", fetch=True) or []
            if any(str(r.get("Msg_type")).lower() == "error" for r in rows):
                return False
        return True

    def optimize(self) -> None:
        for table in self.list_tables():
            if re.fullmatch(r"\w+", table):
                self.execute_query(f"ANALYZE TABLE `{table}`", fetch=True)
