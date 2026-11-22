#!/usr/bin/env python3
"""Move this installation's data from MySQL to a file on this computer (SQLite).

    python scripts/mysql_to_sqlite.py            # copy only; the app keeps using MySQL
    python scripts/mysql_to_sqlite.py --switch   # copy, then make the app use the copy

The MySQL database is only read, never changed. Take a backup first anyway.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from database.mysql_backend import MySQLBackend  # noqa: E402
from database.transfer import copy_mysql_to_sqlite  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", help=f"SQLite file to create (default: {config.Config.sqlite_path()})")
    parser.add_argument("--switch", action="store_true", help="use the new file from now on")
    args = parser.parse_args()

    target = Path(args.target) if args.target else config.Config.sqlite_path()
    cfg = config.Config.DB_CONFIG
    print(f"Copying MySQL {cfg.get('user')}@{cfg.get('host')}/{cfg.get('database')} -> {target}")
    try:
        counts = copy_mysql_to_sqlite(MySQLBackend(cfg), target)
    except Exception as e:
        print(f"Copy failed: {e}")
        return 1
    stale = counts.pop("_stale_links_dropped", 0)
    for table, n in sorted(counts.items()):
        print(f"  {table:<34} {n:>7} rows")
    print(f"Copied {sum(counts.values())} rows; counts verified.")
    if stale:
        print(f"Skipped {stale} leftover link(s) to records that had already been deleted.")

    if args.switch:
        config.Config.DB_BACKEND = "sqlite"
        config.Config.SQLITE_PATH = None if target == config.Config.sqlite_path() else str(target)
        if not config.Config.save_user_settings():
            print("Could not save the settings; the app is still using MySQL.")
            return 1
        print("The program will now use the copy on this computer. Your MySQL database is unchanged.")
    else:
        print("The program still uses MySQL. Run again with --switch to change over.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
