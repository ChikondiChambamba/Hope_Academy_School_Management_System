# Configuration settings
import hashlib
import json
import os
import secrets
import shutil
import sys
from pathlib import Path


def _resolve_resource_dir() -> Path:
    """Directory containing bundled resources."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resolve_app_dir() -> Path:
    """Directory where the application is launched from."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resolve_user_data_dir() -> Path:
    """Stable writable directory shared by development and packaged runs."""
    override = os.getenv("HOPE_SCHOOL_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "Hope Academy School Management System"

    return Path.home() / ".hope_academy_school_management_system"


# Base/resource directories
RESOURCE_DIR = _resolve_resource_dir()
BASE_DIR = _resolve_app_dir()
USER_DATA_DIR = _resolve_user_data_dir()


# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456",  # Set your MySQL password here
    "database": "school_management",
    "port": 3306,
    "autocommit": True,
}


# Application settings
APP_CONFIG = {
    "name": "Hope Academy School Management System",
    "version": "1.0.0",
    "author": "School Admin",
    "default_term": "Term 1",
    "academic_year": "2025-2026",
}


# Path configurations
PATHS = {
    "assets": RESOURCE_DIR / "assets",
    "data": USER_DATA_DIR,
    "reports": USER_DATA_DIR / "reports",
    "backups": USER_DATA_DIR / "backups",
    "exports": USER_DATA_DIR / "exports",
}


# Create necessary directories
for path in PATHS.values():
    if isinstance(path, Path):
        path.mkdir(parents=True, exist_ok=True)


class Config:
    """Backwards-compatible application configuration."""

    BASE_DIR = BASE_DIR
    RESOURCE_DIR = RESOURCE_DIR
    USER_DATA_DIR = USER_DATA_DIR
    DB_CONFIG = DB_CONFIG
    PATHS = PATHS

    APP_NAME = APP_CONFIG.get("name", "Application")
    VERSION = APP_CONFIG.get("version", "2.0.0")
    AUTHOR = APP_CONFIG.get("author", "Chikondi Chambamba")

    from datetime import datetime

    CURRENT_ACADEMIC_YEAR = APP_CONFIG.get("academic_year", str(datetime.now().year))
    ACADEMIC_YEAR_START_DATE = APP_CONFIG.get("academic_year_start_date", None)
    ACADEMIC_YEAR_END_DATE = APP_CONFIG.get("academic_year_end_date", None)
    TERM_END_DATE = APP_CONFIG.get("term_end_date", None)
    TERM_START_DATE = APP_CONFIG.get("term_start_date", None)
    PREVIOUS_ACADEMIC_YEAR = APP_CONFIG.get("previous_academic_year", None)
    PREVIOUS_TERM = APP_CONFIG.get("previous_term", None)
    CURRENT_USER_ROLE = APP_CONFIG.get("default_role", "Administrator")
    CURRENT_TERM = APP_CONFIG.get("default_term", "Term 1")
    TERMS = ["Term 1", "Term 2", "Term 3"]
    TERM_SCHEDULE = APP_CONFIG.get(
        "term_schedule",
        {
            "Term 1": {"start_date": None, "end_date": None},
            "Term 2": {"start_date": None, "end_date": None},
            "Term 3": {"start_date": None, "end_date": None},
        },
    )

    FILES = {"date_format": "%Y-%m-%d"}

    UI = {
        "theme": "clam",
        "primary_color": "#2E86C1",
        "secondary_color": "#28B463",
        "warning_color": "#F39C12",
        "danger_color": "#E74C3C",
        "font_family": "Segoe UI",
        "font_size_title": 16,
        "font_size_large": 12,
        "font_size_small": 10,
    }

    CURRENCY_SYMBOL = "MK "
    CURRENCY_CODE = "MWK"
    CURRENCY_NAME = "Malawian Kwacha"
    PHONE_COUNTRY_CODE = "+265"

    USE_RANDOM_IDS = False
    THEME_MODE = "light"

    VALIDATION = {"min_student_age": 3, "max_student_age": 18}

    SCHOOL_NAME = APP_CONFIG.get("name", "Primary School")
    SCHOOL_ADDRESS = APP_CONFIG.get("address", "Zomba,Chinamwali , Malawi")
    SCHOOL_PHONE = APP_CONFIG.get("phone", "0885159301")
    SCHOOL_EMAIL = APP_CONFIG.get("email", "HopeAcademy@org.com")

    USERS = {}
    CURRENT_USER = None

    PERMISSIONS = {
        "Administrator": {
            "dashboard",
            "students",
            "teachers",
            "attendance",
            "finance",
            "inventory",
            "reports",
            "financial_reports",
            "student_finance",
        },
        "Headteacher": {"dashboard", "students", "teachers", "attendance", "reports"},
        "Finance": {"dashboard", "finance", "financial_reports", "student_finance"},
        "Inventory": {"dashboard", "inventory"},
    }

    @staticmethod
    def get_log_file() -> Path:
        log_dir = Path(Config.PATHS.get("data", Config.USER_DATA_DIR)) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "app.log"

    @staticmethod
    def _write_config_log(message: str, level: str = "INFO") -> None:
        try:
            from datetime import datetime

            log_file = Config.get_log_file()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a", encoding="utf-8") as handle:
                handle.write(f"{timestamp} - config - {level} - {message}\n")
        except Exception:
            pass

    @staticmethod
    def get_backup_filename() -> Path:
        from datetime import datetime

        fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        backup_dir = Path(Config.PATHS.get("backups", Config.USER_DATA_DIR / "backups"))
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir / fname

    @staticmethod
    def get_export_filename(prefix: str = "export") -> Path:
        from datetime import datetime

        fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        export_dir = Path(Config.PATHS.get("exports", Config.USER_DATA_DIR / "exports"))
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir / fname

    PREVIEW_LIMIT = 50

    @staticmethod
    def _user_settings_path() -> Path:
        return Path(Config.PATHS.get("data", Config.USER_DATA_DIR)) / "user_settings.json"

    @staticmethod
    def _legacy_user_settings_paths() -> list[Path]:
        candidates = []
        for root in {
            Config.BASE_DIR,
            Config.RESOURCE_DIR,
            Path.cwd(),
        }:
            if not root:
                continue
            candidates.append(root / "data" / "user_settings.json")
            candidates.append(root / "user_settings.json")
        return [path for path in candidates if path != Config._user_settings_path()]

    @staticmethod
    def _ensure_user_settings_home() -> None:
        Config._user_settings_path().parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _migrate_legacy_user_settings() -> Path:
        target = Config._user_settings_path()
        if target.exists():
            return target

        for legacy_path in Config._legacy_user_settings_paths():
            try:
                if not legacy_path.exists():
                    continue
                Config._ensure_user_settings_home()
                shutil.copy2(legacy_path, target)
                Config._write_config_log(
                    f"Migrated user settings from '{legacy_path}' to '{target}'."
                )
                return target
            except Exception as exc:
                Config._write_config_log(
                    f"Failed migrating legacy settings from '{legacy_path}' to '{target}': {exc}",
                    level="WARNING",
                )
        return target

    @staticmethod
    def _normalize_db_config(raw: dict | None) -> dict:
        normalized = dict(DB_CONFIG)
        if isinstance(raw, dict):
            for key in ("host", "user", "password", "database", "port", "autocommit"):
                if key in raw:
                    normalized[key] = raw[key]
        return normalized

    @staticmethod
    def runtime_context() -> dict:
        return {
            "frozen": bool(getattr(sys, "frozen", False)),
            "resource_dir": str(Config.RESOURCE_DIR),
            "base_dir": str(Config.BASE_DIR),
            "user_data_dir": str(Config.USER_DATA_DIR),
            "settings_path": str(Config._user_settings_path()),
            "db_host": Config.DB_CONFIG.get("host"),
            "db_name": Config.DB_CONFIG.get("database"),
            "db_user": Config.DB_CONFIG.get("user"),
            "current_term": getattr(Config, "CURRENT_TERM", None),
            "academic_year": getattr(Config, "CURRENT_ACADEMIC_YEAR", None),
        }

    @staticmethod
    def log_runtime_context(reason: str = "startup") -> None:
        context = Config.runtime_context()
        Config._write_config_log(
            f"Runtime context ({reason}): frozen={context['frozen']}, "
            f"resource_dir='{context['resource_dir']}', base_dir='{context['base_dir']}', "
            f"user_data_dir='{context['user_data_dir']}', settings_path='{context['settings_path']}', "
            f"db={context['db_user']}@{context['db_host']}/{context['db_name']}, "
            f"current_term='{context['current_term']}', academic_year='{context['academic_year']}'"
        )

    @staticmethod
    def load_user_settings():
        path = Config._migrate_legacy_user_settings()
        try:
            Config.log_runtime_context("before_load_user_settings")
            if path.exists():
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)

                if "DB_CONFIG" in data and isinstance(data["DB_CONFIG"], dict):
                    Config.DB_CONFIG.clear()
                    Config.DB_CONFIG.update(Config._normalize_db_config(data["DB_CONFIG"]))

                if "UI" in data and isinstance(data["UI"], dict):
                    Config.UI.update(data["UI"])

                if "CURRENT_ACADEMIC_YEAR" in data:
                    Config.CURRENT_ACADEMIC_YEAR = data["CURRENT_ACADEMIC_YEAR"]
                if "ACADEMIC_YEAR_START_DATE" in data:
                    Config.ACADEMIC_YEAR_START_DATE = data["ACADEMIC_YEAR_START_DATE"]
                if "ACADEMIC_YEAR_END_DATE" in data:
                    Config.ACADEMIC_YEAR_END_DATE = data["ACADEMIC_YEAR_END_DATE"]
                if "TERM_END_DATE" in data:
                    Config.TERM_END_DATE = data["TERM_END_DATE"]
                if "TERM_START_DATE" in data:
                    Config.TERM_START_DATE = data["TERM_START_DATE"]
                if "CURRENT_TERM" in data:
                    Config.CURRENT_TERM = data["CURRENT_TERM"]
                if "TERM_SCHEDULE" in data and isinstance(data["TERM_SCHEDULE"], dict):
                    normalized_schedule = {}
                    for term_name in Config.TERMS:
                        term_info = data["TERM_SCHEDULE"].get(term_name, {})
                        if not isinstance(term_info, dict):
                            term_info = {}
                        normalized_schedule[term_name] = {
                            "start_date": term_info.get("start_date"),
                            "end_date": term_info.get("end_date"),
                        }
                    Config.TERM_SCHEDULE = normalized_schedule
                if "PREVIOUS_ACADEMIC_YEAR" in data:
                    Config.PREVIOUS_ACADEMIC_YEAR = data["PREVIOUS_ACADEMIC_YEAR"]
                if "PREVIOUS_TERM" in data:
                    Config.PREVIOUS_TERM = data["PREVIOUS_TERM"]
                if "CURRENT_USER_ROLE" in data:
                    Config.CURRENT_USER_ROLE = data["CURRENT_USER_ROLE"]
                if "USERS" in data and isinstance(data["USERS"], dict):
                    normalized_users = {}
                    for username, value in data["USERS"].items():
                        if isinstance(value, dict):
                            normalized_users[username] = value
                        else:
                            normalized_users[username] = {"role": value, "password": None}
                    Config.USERS = normalized_users
                if "CURRENT_USER" in data:
                    Config.CURRENT_USER = data["CURRENT_USER"]

                Config._write_config_log(
                    f"Loaded user settings from '{path}'. "
                    f"CURRENT_TERM='{Config.CURRENT_TERM}', "
                    f"CURRENT_ACADEMIC_YEAR='{Config.CURRENT_ACADEMIC_YEAR}', "
                    f"db={Config.DB_CONFIG.get('user')}@{Config.DB_CONFIG.get('host')}/{Config.DB_CONFIG.get('database')}"
                )
            else:
                Config._write_config_log(
                    f"No user settings file found at '{path}'. Using defaults."
                )
        except Exception as exc:
            Config._write_config_log(
                f"Failed loading user settings from '{path}': {exc}",
                level="ERROR",
            )

    @staticmethod
    def save_user_settings():
        path = Config._user_settings_path()
        try:
            Config._ensure_user_settings_home()

            def _serialize(value):
                from datetime import date, datetime

                if isinstance(value, (date, datetime)):
                    return value.strftime(Config.FILES.get("date_format", "%Y-%m-%d"))
                return value

            payload = {
                "DB_CONFIG": _serialize(dict(Config.DB_CONFIG)),
                "UI": _serialize(dict(Config.UI)),
                "CURRENT_ACADEMIC_YEAR": _serialize(Config.CURRENT_ACADEMIC_YEAR),
                "ACADEMIC_YEAR_START_DATE": _serialize(getattr(Config, "ACADEMIC_YEAR_START_DATE", None)),
                "ACADEMIC_YEAR_END_DATE": _serialize(getattr(Config, "ACADEMIC_YEAR_END_DATE", None)),
                "TERM_END_DATE": _serialize(Config.TERM_END_DATE),
                "TERM_START_DATE": _serialize(getattr(Config, "TERM_START_DATE", None)),
                "CURRENT_TERM": _serialize(getattr(Config, "CURRENT_TERM", None)),
                "TERM_SCHEDULE": _serialize(getattr(Config, "TERM_SCHEDULE", {})),
                "PREVIOUS_ACADEMIC_YEAR": _serialize(getattr(Config, "PREVIOUS_ACADEMIC_YEAR", None)),
                "PREVIOUS_TERM": _serialize(getattr(Config, "PREVIOUS_TERM", None)),
                "CURRENT_USER_ROLE": _serialize(Config.CURRENT_USER_ROLE),
                "USERS": _serialize(getattr(Config, "USERS", {})),
                "CURRENT_USER": _serialize(getattr(Config, "CURRENT_USER", None)),
            }

            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)

            Config._write_config_log(
                f"Saved user settings to '{path}'. "
                f"CURRENT_TERM='{Config.CURRENT_TERM}', "
                f"CURRENT_ACADEMIC_YEAR='{Config.CURRENT_ACADEMIC_YEAR}', "
                f"db={Config.DB_CONFIG.get('user')}@{Config.DB_CONFIG.get('host')}/{Config.DB_CONFIG.get('database')}"
            )
            return True
        except Exception as exc:
            Config._write_config_log(
                f"Failed saving user settings to '{path}': {exc}",
                level="ERROR",
            )
            return False

    @staticmethod
    def get_term_date_range(term_name: str = None):
        term_name = term_name or getattr(Config, "CURRENT_TERM", None)
        schedule = getattr(Config, "TERM_SCHEDULE", {}) or {}
        info = schedule.get(term_name, {}) if isinstance(schedule, dict) else {}
        return (info.get("start_date"), info.get("end_date"))

    @staticmethod
    def get_users():
        out = {}
        for username, info in (Config.USERS or {}).items():
            if isinstance(info, dict):
                out[username] = info.get("role")
            else:
                out[username] = info
        return out

    @staticmethod
    def get_user_info(username: str):
        return (Config.USERS or {}).get(username)

    @staticmethod
    def _hash_password(password: str) -> str:
        if password is None:
            return None
        iterations = 100_000
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return f"{iterations}${salt.hex()}${digest.hex()}"

    @staticmethod
    def _verify_password(stored: str, provided: str) -> bool:
        try:
            if not stored:
                return False
            parts = stored.split("$")
            if len(parts) != 3:
                return False
            iterations = int(parts[0])
            salt = bytes.fromhex(parts[1])
            expected = parts[2]
            digest = hashlib.pbkdf2_hmac("sha256", provided.encode("utf-8"), salt, iterations)
            return secrets.compare_digest(digest.hex(), expected)
        except Exception:
            return False

    @staticmethod
    def add_user(username: str, role: str, password: str = None):
        if not username:
            return False
        Config.USERS[username] = {
            "role": role,
            "password": Config._hash_password(password) if password else None,
        }
        return Config.save_user_settings()

    @staticmethod
    def remove_user(username: str):
        if username in Config.USERS:
            del Config.USERS[username]
            return Config.save_user_settings()
        return False

    @staticmethod
    def set_current_user(username: str):
        if username and username in Config.USERS:
            Config.CURRENT_USER = username
            info = Config.USERS.get(username)
            Config.CURRENT_USER_ROLE = info.get("role") if isinstance(info, dict) else info
            return Config.save_user_settings()
        return False

    @staticmethod
    def set_user_role(username: str, role: str):
        if username in Config.USERS:
            info = Config.USERS.get(username)
            if not isinstance(info, dict):
                info = {"role": info, "password": None}
            info["role"] = role
            Config.USERS[username] = info
            if Config.CURRENT_USER == username:
                Config.CURRENT_USER_ROLE = role
            return Config.save_user_settings()
        return False

    @staticmethod
    def set_user_password(username: str, password: str) -> bool:
        if username not in Config.USERS:
            return False
        try:
            info = Config.USERS.get(username)
            if not isinstance(info, dict):
                info = {"role": info, "password": None}
            info["password"] = Config._hash_password(password) if password else None
            Config.USERS[username] = info
            return Config.save_user_settings()
        except Exception:
            return False

    @staticmethod
    def verify_user_credentials(username: str, password: str) -> bool:
        info = Config.USERS.get(username)
        if not info or not isinstance(info, dict):
            return False
        stored = info.get("password")
        if not stored:
            return False
        return Config._verify_password(stored, password)

    @staticmethod
    def has_permission(feature: str) -> bool:
        try:
            role = getattr(Config, "CURRENT_USER_ROLE", "Administrator")
            allowed = Config.PERMISSIONS.get(role, set())
            return feature in allowed
        except Exception:
            return False


# Load user settings at import time
Config.load_user_settings()
