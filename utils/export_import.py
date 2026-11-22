"""Backup, restore and export.

* SQLite ("on this computer"): a backup is a consistent copy of the data
  file; restoring swaps the file in after saving a safety copy of the current
  one. The application also keeps automatic daily backups.
* MySQL: uses the mysqldump / mysql tools from the MySQL installation.
"""
import csv
import logging
import os
import shutil
import subprocess
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Tuple

import config
from database.connection import db

logger = logging.getLogger(__name__)

AUTO_BACKUP_PREFIX = "auto_"
AUTO_BACKUPS_KEPT = 14


def backup_extension() -> str:
    return ".db" if config.Config.DB_BACKEND == "sqlite" else ".sql"


def _backup_dir() -> Path:
    path = Path(config.Config.PATHS['backups'])
    path.mkdir(parents=True, exist_ok=True)
    return path


# --- MySQL client tools -------------------------------------------------------

def _mysql_tool(name: str) -> Optional[str]:
    """Locate mysql/mysqldump on PATH or in the standard Windows install folders."""
    found = shutil.which(name)
    if found:
        return found
    for base in (os.getenv("ProgramFiles", r"C:\Program Files"), os.getenv("ProgramFiles(x86)", "")):
        if not base:
            continue
        for candidate in sorted(Path(base, "MySQL").glob(f"MySQL Server*/bin/{name}.exe"), reverse=True):
            return str(candidate)
    return None


def _mysql_command(tool: str):
    cfg = config.Config.DB_CONFIG
    exe = _mysql_tool(tool)
    if not exe:
        raise RuntimeError(f"The MySQL '{tool}' program was not found on this computer.")
    cmd = [exe, '-h', str(cfg.get('host', 'localhost')), '-P', str(cfg.get('port', 3306)), '-u', str(cfg.get('user', ''))]
    env = dict(os.environ, MYSQL_PWD=str(cfg.get('password') or ''))  # keeps the password off the command line
    return cmd, env


# --- backup / restore ---------------------------------------------------------

def backup_database(output_path: str = None) -> bool:
    """Write a full backup. Returns True on success."""
    target = Path(output_path) if output_path else _backup_dir() / (
        f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{backup_extension()}")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if db.is_sqlite:
            db.backend.backup_to(target)
        else:
            cmd, env = _mysql_command('mysqldump')
            cmd += ['--single-transaction', '--routines', '--triggers', config.Config.DB_CONFIG['database']]
            with open(target, 'wb') as handle:
                subprocess.run(cmd, stdout=handle, env=env, check=True)
        logger.info(f"Database backed up to {target}")
        return True
    except Exception as e:
        logger.exception(f"Backup failed: {e}")
        try:
            if target.exists() and target.stat().st_size == 0:
                target.unlink()
        except OSError:
            pass
        return False


def restore_database(backup_file: str) -> Tuple[bool, str]:
    """Replace the current data with a backup. Returns (success, message)."""
    source = Path(backup_file)
    if not source.is_file():
        return False, "The selected backup file does not exist."
    try:
        if db.is_sqlite:
            from database.sqlite_backend import is_school_database
            if not is_school_database(source):
                return False, "The selected file is not a backup made by this application."
            current = config.Config.sqlite_path()
            safety = _backup_dir() / f"before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            db.backend.backup_to(safety)
            db.reset()
            for suffix in ("-wal", "-shm"):
                Path(f"{current}{suffix}").unlink(missing_ok=True)
            shutil.copy2(source, current)
            db.prepare()  # upgrades an older backup to the current schema
            return True, f"Data restored. Your previous data was saved to:\n{safety}"
        cmd, env = _mysql_command('mysql')
        cmd.append(config.Config.DB_CONFIG['database'])
        with open(source, 'rb') as handle:
            subprocess.run(cmd, stdin=handle, env=env, check=True)
        db.reset()
        return True, "Database restored."
    except Exception as e:
        logger.exception(f"Restore failed: {e}")
        return False, f"Restore failed: {e}"


def run_automatic_backup() -> Optional[Path]:
    """Once per day, keep a copy of the SQLite data file (the newest 14 are kept)."""
    if config.Config.DB_BACKEND != "sqlite" or not config.Config.sqlite_path().exists():
        return None
    folder = _backup_dir()
    today = f"{AUTO_BACKUP_PREFIX}{date.today().strftime('%Y%m%d')}.db"
    target = folder / today
    if target.exists():
        return None
    if not backup_database(str(target)):
        return None
    autos = sorted(folder.glob(f"{AUTO_BACKUP_PREFIX}*.db"))
    for old in autos[:-AUTO_BACKUPS_KEPT]:
        try:
            old.unlink()
        except OSError:
            pass
    return target


# --- export / import ----------------------------------------------------------

def export_all_data(output_dir: str = None) -> Optional[Path]:
    """Export every table to CSV in a new dated folder. Returns the folder, or None."""
    try:
        base = Path(output_dir) if output_dir else Path(config.Config.PATHS['exports'])
        out_dir = base / f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for table_name in db.list_tables():
            rows = db.execute_query(f"SELECT * FROM {table_name}", fetch=True) or []
            with open(out_dir / f"{table_name}.csv", 'w', newline='', encoding='utf-8-sig') as handle:
                if rows:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
        logger.info(f"Exported all tables to {out_dir}")
        return out_dir
    except Exception as e:
        logger.exception(f"export_all_data failed: {e}")
        return None


def import_from_excel(file_path: str) -> Tuple[bool, str]:
    """Bulk import is not implemented yet."""
    return False, ("Importing from Excel is not available yet.\n"
                   "Add records through the Students, Teachers, Finance and Inventory tabs.")


__all__ = [
    'backup_database',
    'restore_database',
    'run_automatic_backup',
    'export_all_data',
    'import_from_excel',
    'backup_extension',
]
