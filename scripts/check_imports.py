modules = [
    'main',
    'UI.main_window',
    'UI.dashboard',
    'UI.students',
    'UI.teachers',
    'UI.finance',
    'UI.inventory',
    'UI.attendance',
    'UI.reports',
    'UI.reports_tab',
    'UI.dialogs',
    'utils.helpers',
    'utils.export_import',
    'utils.validators',
    'models.student',
    'models.teacher',
    'models.finance',
    'models.expense_category',
    'models.attendance',
    'models.inventory',
    'reports.generators.student_reports',
    'reports.generators.financial_reports',
    'reports.generators.inventory_reports'
]

import importlib
import sys
from pathlib import Path

# Ensure repo root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

failed = []
for m in modules:
    try:
        importlib.import_module(m)
        print(f"OK: {m}")
    except Exception as e:
        print(f"FAIL: {m} -> {e}")
        failed.append((m, str(e)))

print('\nSummary:')
if not failed:
    print('All imports OK')
else:
    print(f'{len(failed)} failures:')
    for m,e in failed:
        print(f' - {m}: {e}')
