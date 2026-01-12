# Configuration settings
import os
from pathlib import Path
import json

# Base directory
BASE_DIR = Path(__file__).parent

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # Set your MySQL password here
    'database': 'school_management',
    'port': 3306,
    'autocommit': True
}

# Application settings
APP_CONFIG = {
    'name': 'Hope Academy School Management System',
    'version': '1.0.0',
    'author': 'School Admin',
    'default_term': 'Term 2',
    'academic_year': '2025-2026',
}

# Path configurations
PATHS = {
    'assets': BASE_DIR / 'assets',
    'data': BASE_DIR / 'data',
    'reports': BASE_DIR / 'reports',
    'backups': BASE_DIR / 'data' / 'backups',
    'exports': BASE_DIR / 'data' / 'exports'
}

# Create necessary directories
for path in PATHS.values():
    if isinstance(path, Path):
        path.mkdir(parents=True, exist_ok=True)


# Backwards-compatible `Config` class for modules that expect `config.Config`
class Config:
    BASE_DIR = BASE_DIR
    DB_CONFIG = DB_CONFIG
    PATHS = PATHS

    APP_NAME = APP_CONFIG.get('name', 'Application')
    VERSION = APP_CONFIG.get('version', '2.0.0')
    AUTHOR = APP_CONFIG.get('author', 'Chikondi Chambamba')

    from datetime import datetime
    # Loadable setting - can be updated via Preferences UI
    CURRENT_ACADEMIC_YEAR = APP_CONFIG.get('academic_year', str(datetime.now().year))
    TERM_END_DATE = APP_CONFIG.get('term_end_date', None)
    # Explicitly define TERM_START_DATE so it's always present on the Config class
    TERM_START_DATE = APP_CONFIG.get('term_start_date', None)
    CURRENT_USER_ROLE = APP_CONFIG.get('default_role', 'Administrator')
    CURRENT_TERM = APP_CONFIG.get('default_term', 'Term 1')
    TERMS = ['Term 1', 'Term 2', 'Term 3']

    FILES = {'date_format': '%Y-%m-%d'}

    UI = {
        'theme': 'clam',
        'primary_color': '#2E86C1',
        'secondary_color': '#28B463',
        'warning_color': '#F39C12',
        'danger_color': '#E74C3C',
        'font_family': 'Segoe UI',
        'font_size_title': 16,
        'font_size_large': 12,
        'font_size_small': 10
    }

    # Currency and phone settings
    CURRENCY_SYMBOL = 'MK '
    CURRENCY_CODE = 'MWK'
    CURRENCY_NAME = 'Malawian Kwacha'
    PHONE_COUNTRY_CODE = '+265'

    # ID generation
    USE_RANDOM_IDS = False  # Set True to use random/generated IDs for students/teachers

    # Theme mode: 'light' or 'dark'
    THEME_MODE = 'light'

    VALIDATION = {
        'min_student_age': 3,
        'max_student_age': 18
    }

    # School identity defaults (used in UI and reports)
    SCHOOL_NAME = APP_CONFIG.get('name', 'Primary School')
    SCHOOL_ADDRESS = APP_CONFIG.get('address', 'Zomba,Chinamwali , Malawi')
    SCHOOL_PHONE = APP_CONFIG.get('phone', '0885159301')
    SCHOOL_EMAIL = APP_CONFIG.get('email', 'HopeAcademy@org.com')

    @staticmethod
    def get_log_file():
        log_dir = Path(Config.PATHS.get('data', Config.BASE_DIR / 'data')) / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / 'app.log'

    @staticmethod
    def get_backup_filename():
        from datetime import datetime
        fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        backup_dir = Path(Config.PATHS.get('backups', Config.BASE_DIR / 'data' / 'backups'))
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir / fname

    @staticmethod
    def get_export_filename(prefix='export'):
        from datetime import datetime
        fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        export_dir = Path(Config.PATHS.get('exports', Config.BASE_DIR / 'data' / 'exports'))
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir / fname

    # Preview/pagination defaults
    PREVIEW_LIMIT = 1000


    @staticmethod
    def _user_settings_path() -> Path:
        return Path(Config.PATHS.get('data', Config.BASE_DIR / 'data')) / 'user_settings.json'

    @staticmethod
    def load_user_settings():
        path = Config._user_settings_path()
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'CURRENT_ACADEMIC_YEAR' in data:
                        Config.CURRENT_ACADEMIC_YEAR = data['CURRENT_ACADEMIC_YEAR']
                    if 'TERM_END_DATE' in data:
                        # TERM_END_DATE may be stored as a string; keep as-is
                        Config.TERM_END_DATE = data['TERM_END_DATE']
                    if 'TERM_START_DATE' in data:
                        # TERM_START_DATE stored as string in YYYY-MM-DD format
                        Config.TERM_START_DATE = data['TERM_START_DATE']
                    if 'CURRENT_TERM' in data:
                        Config.CURRENT_TERM = data['CURRENT_TERM']
                    if 'CURRENT_USER_ROLE' in data:
                        Config.CURRENT_USER_ROLE = data['CURRENT_USER_ROLE']
                    # Users storage: mapping username -> role
                    if 'USERS' in data and isinstance(data['USERS'], dict):
                        Config.USERS = data['USERS']
                    if 'CURRENT_USER' in data:
                        Config.CURRENT_USER = data['CURRENT_USER']
        except Exception:
            pass

    @staticmethod
    def save_user_settings():
        path = Config._user_settings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            def _serialize(v):
                # Convert date/datetime objects to string using configured format
                from datetime import date, datetime
                if isinstance(v, (date, datetime)):
                    return v.strftime(Config.FILES.get('date_format', '%Y-%m-%d'))
                return v

            payload = {
                'CURRENT_ACADEMIC_YEAR': _serialize(Config.CURRENT_ACADEMIC_YEAR),
                'TERM_END_DATE': _serialize(Config.TERM_END_DATE),
                'TERM_START_DATE': _serialize(getattr(Config, 'TERM_START_DATE', None)),
                'CURRENT_TERM': _serialize(getattr(Config, 'CURRENT_TERM', None)),
                'CURRENT_USER_ROLE': _serialize(Config.CURRENT_USER_ROLE),
                'USERS': _serialize(getattr(Config, 'USERS', {})),
                'CURRENT_USER': _serialize(getattr(Config, 'CURRENT_USER', None))
            }

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
            return True
        except Exception:
            # If writing fails, do not raise — but return False so callers can log/handle
            return False

    # Simple user management (stored in user_settings.json)
    USERS = {}
    CURRENT_USER = None
    
    # Role-based permissions map
    PERMISSIONS = {
        'Administrator': {
            'dashboard', 'students', 'teachers', 'attendance', 'finance', 'inventory', 'reports', 'financial_reports', 'student_finance'
        },
        'Headteacher': {
            'dashboard', 'students', 'teachers', 'attendance', 'reports'
        },
        'Finance': {
            'dashboard', 'finance', 'inventory', 'financial_reports', 'student_finance'
        },
        'Inventory': {
            'dashboard', 'inventory'
        }
    }

    @staticmethod
    def get_users():
        return dict(Config.USERS or {})

    @staticmethod
    def add_user(username: str, role: str):
        if not username:
            return False
        Config.USERS[username] = role
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
            Config.CURRENT_USER_ROLE = Config.USERS[username]
            return Config.save_user_settings()
        return False

    @staticmethod
    def set_user_role(username: str, role: str):
        if username in Config.USERS:
            Config.USERS[username] = role
            # if changing current user's role, update CURRENT_USER_ROLE
            if Config.CURRENT_USER == username:
                Config.CURRENT_USER_ROLE = role
            return Config.save_user_settings()
        return False

    @staticmethod
    def has_permission(feature: str) -> bool:
        """Return True if the current role is allowed to access the given feature."""
        try:
            role = getattr(Config, 'CURRENT_USER_ROLE', 'Administrator')
            allowed = Config.PERMISSIONS.get(role, set())
            return feature in allowed
        except Exception:
            return False

# Load user settings at import time
Config.load_user_settings()