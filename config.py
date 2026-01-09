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
    VERSION = APP_CONFIG.get('version', '0.0.0')
    AUTHOR = APP_CONFIG.get('author', '')

    from datetime import datetime
    # Loadable setting - can be updated via Preferences UI
    CURRENT_ACADEMIC_YEAR = APP_CONFIG.get('academic_year', str(datetime.now().year))
    TERM_END_DATE = APP_CONFIG.get('term_end_date', None)
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
                        Config.TERM_END_DATE = data['TERM_END_DATE']
        except Exception:
            pass

    @staticmethod
    def save_user_settings():
        path = Config._user_settings_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'CURRENT_ACADEMIC_YEAR': Config.CURRENT_ACADEMIC_YEAR,
                    'TERM_END_DATE': Config.TERM_END_DATE
                }, f, indent=2)
            return True
        except Exception:
            return False

# Load user settings at import time
Config.load_user_settings()