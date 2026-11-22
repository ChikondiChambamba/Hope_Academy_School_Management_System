"""Shared test bootstrap: isolate settings and replace the database with a fake.

Import this module before importing anything from the application.
"""
import os
import sys
import tempfile
import types
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Never read or write the real user settings while testing.
os.environ["HOPE_SCHOOL_DATA_DIR"] = tempfile.mkdtemp(prefix="hope_tests_")

class _SwitchableDB:
    """Stands in for `database.connection.db`.

    Unit tests get a MagicMock (no database at all). Integration tests call
    `use_database(backend)` to run the application's real SQL against a
    temporary SQLite file.
    """

    def __init__(self):
        object.__setattr__(self, "target", mock.MagicMock(name="db"))

    def __getattr__(self, name):
        return getattr(self.target, name)

    def __setattr__(self, name, value):
        setattr(self.target, name, value)


# Replace the database module so tests never touch a real server.
fake_db = _SwitchableDB()
_fake_connection_module = types.ModuleType("database.connection")
_fake_connection_module.db = fake_db
_fake_connection_module.DatabaseNotConfigured = RuntimeError
_fake_connection_module.DatabaseConnection = mock.MagicMock(name="DatabaseConnection")
sys.modules["database.connection"] = _fake_connection_module

import config  # noqa: E402


def use_database(target):
    """Point every module's `db` at `target` (a backend, or a MagicMock)."""
    object.__setattr__(fake_db, "target", target)


def reset_database():
    use_database(mock.MagicMock(name="db"))

# Discard anything the legacy-settings migration may have copied in from a
# developer checkout, so every test starts from a clean, user-less state.
config.Config.USERS = {}
config.Config.CURRENT_USER = None
config.Config._sync_current_role()
