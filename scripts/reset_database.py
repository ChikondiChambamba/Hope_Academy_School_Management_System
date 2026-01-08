#!/usr/bin/env python3
"""Reset the application's database to the schema in database/schema.sql

This script will:
- create a timestamped backup of the database (uses mysqldump if available)
- drop the database if it exists
- recreate the database and run `database/schema.sql` via setup_database.create_database()

Usage:
  python scripts/reset_database.py [--yes]

Be careful: this is destructive. Backups are placed under `database/backups/`.
"""
import os
import sys
import shutil
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
DB_BACKUP_DIR = os.path.join(ROOT, 'database', 'backups')

def make_backup(db_config):
    os.makedirs(DB_BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(DB_BACKUP_DIR, f"backup_{db_config['database']}_{ts}.sql")

    mysqldump = shutil.which('mysqldump')
    if mysqldump:
        print(f"Found mysqldump at {mysqldump}, creating SQL dump to {backup_file} ...")
        cmd = [mysqldump, '-h', db_config.get('host', 'localhost'), '-u', db_config.get('user', ''), f"-p{db_config.get('password','')}", db_config['database']]
        try:
            with open(backup_file, 'wb') as f:
                subprocess.run(cmd, stdout=f, check=True)
            print('Backup completed.')
            return backup_file
        except subprocess.CalledProcessError as e:
            print('mysqldump failed:', e)
            return None
    else:
        print('mysqldump not found; skipping external dump. No binary backup created.')
        return None

def drop_database(db_config):
    # Drop database using mysql.connector
    try:
        import mysql.connector
        conn_cfg = db_config.copy()
        conn_cfg.pop('database', None)
        conn = mysql.connector.connect(**conn_cfg)
        cur = conn.cursor()
        print(f"Dropping database {db_config['database']} if exists...")
        cur.execute(f"DROP DATABASE IF EXISTS {db_config['database']}")
        conn.commit()
        cur.close()
        conn.close()
        print('Dropped database (if it existed).')
        return True
    except Exception as e:
        print('Failed to drop database:', e)
        return False

def recreate_from_schema():
    # Reuse setup_database.create_database() which executes database/schema.sql
    try:
        sys.path.insert(0, ROOT)
        import setup_database
        ok = setup_database.create_database()
        return ok
    except Exception as e:
        print('Failed to recreate database from schema:', e)
        return False

def verify(db_config):
    try:
        import mysql.connector
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = cur.fetchall()
        print(f"Found {len(tables)} tables after reset:")
        for t in tables:
            print(' -', t[0])
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print('Verification failed:', e)
        return False

def main():
    # Ensure project root is at front of sys.path so local config.py is imported
    sys.path.insert(0, ROOT)
    import config
    # Support both top-level DB_CONFIG and backward-compatible Config.DB_CONFIG
    if hasattr(config, 'DB_CONFIG'):
        db_config = config.DB_CONFIG.copy()
    elif hasattr(config, 'Config') and hasattr(config.Config, 'DB_CONFIG'):
        db_config = dict(config.Config.DB_CONFIG)
    else:
        print('Could not find DB configuration in config.py')
        print('config module file:', getattr(config, '__file__', None))
        try:
            print('config attributes:', [k for k in dir(config) if not k.startswith('__')])
        except Exception:
            pass
        # Debug import locations
        try:
            import importlib.util
            spec = importlib.util.find_spec('config')
            print('importlib spec for config:', spec)
            print('sys.path (first 8 entries):', sys.path[:8])
        except Exception:
            pass
        return

    print('\nWARNING: This will reset the database to the contents of database/schema.sql')
    print('All existing data will be lost unless you have a backup.')

    confirm = '--yes' in sys.argv or input('Proceed and overwrite database? (y/N): ').strip().lower() == 'y'
    if not confirm:
        print('Aborted by user.')
        return

    # Step 1: backup
    print('\nStep 1: creating backup (if possible)')
    backup = make_backup(db_config)
    if backup:
        print('Backup file:', backup)
    else:
        print('No binary dump created. Proceeding may lose data.')

    # Step 2: drop database
    print('\nStep 2: dropping database')
    if not drop_database(db_config):
        print('Could not drop database; aborting.')
        return

    # Step 3: recreate
    print('\nStep 3: recreating database from schema')
    if not recreate_from_schema():
        print('Failed to recreate database. See errors above.')
        return

    # Step 4: verify
    print('\nStep 4: verifying')
    if verify(db_config):
        print('\nDatabase reset completed successfully.')
    else:
        print('\nDatabase reset may have failed; check logs.')

if __name__ == '__main__':
    main()
