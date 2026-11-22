#!/usr/bin/env python3
"""
Database setup script for School Management System.

Creates the configured database (config.DB_CONFIG / HOPE_DB_* env vars) if it
does not exist and executes database/schema.sql against it. The schema is
non-destructive; running this against an existing database fails safely on
the first already-existing table instead of overwriting data.
"""
import re
import sys
from pathlib import Path

import mysql.connector
from mysql.connector import Error

import config

SCHEMA_FILE = Path(__file__).resolve().parent / 'database' / 'schema.sql'
_DB_NAME_RE = re.compile(r'^[A-Za-z0-9_]+$')


def split_sql_script(script: str) -> list[str]:
    """Split a MySQL script into statements, honouring `DELIMITER` directives.

    Routines and triggers contain `;` inside BEGIN...END, so they are wrapped in
    `DELIMITER $$ ... $$ DELIMITER ;` blocks in schema.sql, exactly as the mysql
    command-line client expects. Full-line `--` comments are dropped.
    """
    statements: list[str] = []
    delimiter = ';'
    buffer: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith('DELIMITER '):
            delimiter = stripped.split(None, 1)[1]
            continue
        if not buffer and (not stripped or stripped.startswith('--')):
            continue
        buffer.append(line)
        if stripped.endswith(delimiter):
            statement = '\n'.join(buffer).rstrip()[: -len(delimiter)].strip()
            if statement:
                statements.append(statement)
            buffer = []
    tail = '\n'.join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def create_database() -> bool:
    """Create the configured database and run schema.sql. Returns True on success.

    For "on this computer" (SQLite) storage the program does this by itself on
    first launch; this function then just makes sure the data file exists.
    """
    if config.Config.DB_BACKEND == 'sqlite':
        from database.connection import db
        db.prepare()
        print(f"Data file ready: {config.Config.sqlite_path()}")
        return True
    db_name = config.DB_CONFIG['database']
    if not _DB_NAME_RE.match(db_name):
        print(f"Error: invalid database name {db_name!r}")
        return False
    if not SCHEMA_FILE.exists():
        print(f"Error: schema file not found at {SCHEMA_FILE}")
        return False

    server_config = {k: v for k, v in config.DB_CONFIG.items() if k != 'database'}
    statements = split_sql_script(SCHEMA_FILE.read_text(encoding='utf-8-sig'))

    print("=" * 60)
    print(f"  {config.APP_CONFIG['name']} - Database Setup")
    print("=" * 60)
    connection = None
    try:
        print(f"\n1. Connecting to MySQL at {server_config.get('host')}...")
        connection = mysql.connector.connect(**server_config)
        cursor = connection.cursor()

        print(f"2. Creating database '{db_name}' (if missing)...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cursor.execute(f"USE `{db_name}`")

        print(f"3. Executing {len(statements)} schema statements...")
        for number, statement in enumerate(statements, 1):
            try:
                cursor.execute(statement)
                while cursor.nextset():  # drain multi-result statements
                    pass
            except Error as e:
                first_line = statement.splitlines()[0][:80]
                print(f"\nError in statement {number} ({first_line}): {e}")
                if getattr(e, 'errno', None) == 1050:  # ER_TABLE_EXISTS_ERROR
                    print("The database already contains tables. Nothing was overwritten.\n"
                          "Use scripts/reset_database.py to rebuild it deliberately.")
                return False
        connection.commit()

        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\nCreated {len(tables)} tables: {', '.join(sorted(tables))}")
        print("\nDatabase setup completed successfully. Start the app with: python main.py")
        return True

    except Error as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure MySQL server is running")
        print("2. Check credentials (HOPE_DB_* environment variables or Edit > Preferences)")
        print("3. Ensure the MySQL user may create databases")
        return False
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


def main():
    print(f"\nThis will create database '{config.DB_CONFIG['database']}' on "
          f"{config.DB_CONFIG['host']} and create all tables from {SCHEMA_FILE.name}.")
    if input("Continue? (y/n): ").strip().lower() != 'y':
        print("Setup cancelled.")
        sys.exit(0)
    sys.exit(0 if create_database() else 1)


if __name__ == "__main__":
    main()
