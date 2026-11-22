"""
Database access for the whole application.

Every module uses the shared `db` object. It forwards to the storage chosen at
first launch (config.Config.DB_BACKEND):

  * "sqlite" - one file on this computer (default; nothing to install)
  * "mysql"  - an existing MySQL server

The backend is created lazily on first use, so importing this module never
touches a database, and `reset()` switches to new settings.
"""
from typing import List, Optional, Sequence

import config


class DatabaseNotConfigured(RuntimeError):
    """Raised when the database is used before storage has been chosen."""


class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._backend = None
        return cls._instance

    # backend selection
    @property
    def backend(self):
        if self._backend is None:
            choice = config.Config.DB_BACKEND
            if choice == "sqlite":
                from .sqlite_backend import SQLiteBackend
                self._backend = SQLiteBackend(config.Config.sqlite_path())
            elif choice == "mysql":
                from .mysql_backend import MySQLBackend
                self._backend = MySQLBackend(config.Config.DB_CONFIG)
            else:
                raise DatabaseNotConfigured("Choose where to store data before using the database.")
        return self._backend

    @property
    def dialect(self) -> str:
        return self.backend.dialect

    @property
    def is_sqlite(self) -> bool:
        return self.dialect == "sqlite"

    @property
    def manages_schema(self) -> bool:
        """True when the schema file is complete, so runtime CREATE/ALTER must be skipped."""
        return self.backend.manages_schema

    @property
    def write_generation(self) -> int:
        """Increases on every data change; lets read-only results be cached safely."""
        return self.backend.write_generation

    def once(self, key: str) -> bool:
        """True only the first time `key` is seen on the current connection session."""
        return self.backend.once(key)

    def reset(self) -> None:
        """Close connections; the next call reconnects using the current settings."""
        if self._backend is not None:
            self._backend.close()
        self._backend = None

    reset_pool = reset
    close = reset
    close_all = reset

    # queries (signatures unchanged from the MySQL-only version)
    def execute_query(self, query: str, params: Sequence = None, fetch: bool = False):
        return self.backend.execute_query(query, params, fetch=fetch)

    def execute_many(self, query: str, params_list: List[Sequence]) -> None:
        return self.backend.execute_many(query, params_list)

    def transaction(self):
        return self.backend.transaction()

    def execute_query_in_transaction(self, connection, query: str, params: Sequence = None, fetch: bool = False):
        return self.backend.execute_query_in_transaction(connection, query, params, fetch=fetch)

    # schema helpers
    def prepare(self) -> None:
        """Create or upgrade the database (SQLite); no-op for MySQL."""
        self.backend.prepare()

    def test_connection(self) -> bool:
        try:
            return self.backend.test_connection()
        except DatabaseNotConfigured:
            return False

    def table_exists(self, table: str) -> bool:
        return self.backend.table_exists(table)

    def list_tables(self) -> List[str]:
        return self.backend.list_tables()

    def column_exists(self, table: str, column: str) -> bool:
        return self.backend.column_exists(table, column)

    def group_concat_distinct(self, expr: str, separator_literal: str) -> str:
        """SQL for a sorted, de-duplicated, separator-joined list of `expr`."""
        return self.backend.group_concat_distinct(expr, separator_literal)

    def upsert_clause(self, conflict_columns, set_new=(), set_sql=None) -> str:
        """Dialect-correct "insert, or update the existing row" clause (see backends)."""
        return self.backend.upsert_clause(conflict_columns, set_new, set_sql)

    # maintenance
    def integrity_ok(self) -> bool:
        return self.backend.integrity_ok()

    def optimize(self) -> None:
        self.backend.optimize()


# Shared instance
db = DatabaseConnection()
