"""Export/import utilities.

Features:
- `backup_database` uses `mysqldump` when available, otherwise falls back
  to exporting each table as CSV in a timestamped folder.
- `restore_database` prefers `mysql` client; if not available it will
  return False (manual restore recommended).
- `export_all_data` writes per-table CSV files.
- `import_from_excel` is a lightweight stub that suggests using pandas.
"""
from pathlib import Path
import shutil
import subprocess
import csv
from datetime import datetime
import logging
import config

from database.connection import db

logger = logging.getLogger(__name__)


def _db_credentials():
    cfg = config.Config.DB_CONFIG
    return cfg.get('host', 'localhost'), cfg.get('user', ''), cfg.get('password', ''), cfg.get('database', '')


def backup_database(output_path: str = None) -> bool:
    """Backup the database to a SQL dump (preferred) or CSV files (fallback).

    Returns True on success.
    """
    host, user, password, database = _db_credentials()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Preferred: use mysqldump
    mysqldump = shutil.which('mysqldump')
    if mysqldump:
        out_file = Path(output_path or (config.Config.PATHS['backups'] / f"{database}_backup_{timestamp}.sql"))
        out_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = [mysqldump, '-h', host, '-u', user, f"-p{password}", database]
        try:
            with open(out_file, 'wb') as f:
                subprocess.run(cmd, stdout=f, check=True)
            logger.info(f"Database dumped to {out_file}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"mysqldump failed: {e}")
            # fallthrough to CSV fallback

    # Fallback: export each table to CSV
    try:
        out_dir = Path(output_path or (config.Config.PATHS['backups'] / f"{database}_csv_export_{timestamp}"))
        out_dir.mkdir(parents=True, exist_ok=True)

        # Get list of tables
        q = "SELECT table_name FROM information_schema.tables WHERE table_schema = %s"
        tables = db.execute_query(q, (database,), fetch=True)
        for t in tables:
            # column name may vary; pick first value
            table_name = next(iter(t.values()))
            rows = db.execute_query(f"SELECT * FROM `{table_name}`", fetch=True)
            if rows is None:
                rows = []

            if rows:
                cols = list(rows[0].keys())
            else:
                # Get column names via zero-row fetch
                cols = []
            csv_path = out_dir / f"{table_name}.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                if cols:
                    writer = csv.DictWriter(csvfile, fieldnames=cols)
                    writer.writeheader()
                    writer.writerows(rows)
                else:
                    # Empty table, still create headerless file
                    csvfile.write('')

        logger.info(f"Exported tables to CSV in {out_dir}")
        return True
    except Exception as e:
        logger.exception(f"backup_database failed: {e}")
        return False


def restore_database(backup_file: str) -> bool:
    """Restore database from SQL dump using `mysql` client if available.

    If `mysql` client is not available, this function will return False.
    """
    host, user, password, database = _db_credentials()
    mysql = shutil.which('mysql')
    if mysql and Path(backup_file).is_file():
        cmd = [mysql, '-h', host, '-u', user, f"-p{password}", database]
        try:
            with open(backup_file, 'rb') as f:
                subprocess.run(cmd, stdin=f, check=True)
            logger.info(f"Restored database from {backup_file}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"mysql client failed to restore: {e}")
            return False
    else:
        logger.error("mysql client not available or backup file missing; manual restore required")
        return False


def export_all_data(output_dir: str = None) -> bool:
    """Export all tables to CSV files under `output_dir`.

    Returns True on success.
    """
    try:
        host, user, password, database = _db_credentials()
        out_dir = Path(output_dir or config.Config.PATHS['exports'])
        out_dir.mkdir(parents=True, exist_ok=True)

        q = "SELECT table_name FROM information_schema.tables WHERE table_schema = %s"
        tables = db.execute_query(q, (database,), fetch=True)
        for t in tables:
            table_name = next(iter(t.values()))
            rows = db.execute_query(f"SELECT * FROM `{table_name}`", fetch=True)
            csv_path = out_dir / f"{table_name}.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                if rows:
                    cols = list(rows[0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=cols)
                    writer.writeheader()
                    writer.writerows(rows)
                else:
                    # Create empty file for table with no rows
                    csvfile.write('')

        logger.info(f"Exported all tables to {out_dir}")
        return True
    except Exception as e:
        logger.exception(f"export_all_data failed: {e}")
        return False


def import_from_excel(file_path: str) -> bool:
    """Import data from Excel - lightweight stub.

    For robust Excel import, install `pandas` and `openpyxl` and implement
    mapping logic. This stub returns False and logs guidance.
    """
    logger.error("import_from_excel not implemented. Use pandas + openpyxl to implement this feature.")
    return False


__all__ = [
    'backup_database',
    'restore_database',
    'export_all_data',
    'import_from_excel',
]
