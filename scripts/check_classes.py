import sys
import os

# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.connection import db

try:
    res = db.execute_query("SELECT class_id, class_name FROM classes ORDER BY class_name", fetch=True)
    if not res:
        print('NO_CLASSES')
    else:
        for r in res:
            print(f"{r.get('class_id')}\t{r.get('class_name')}")
except Exception as e:
    print('ERROR', str(e))
