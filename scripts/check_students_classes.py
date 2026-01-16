import sys
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.connection import db

try:
    res = db.execute_query("SELECT DISTINCT class FROM students ORDER BY class", fetch=True)
    if not res:
        print('NO_DISTINCT_CLASSES_IN_STUDENTS')
    else:
        for r in res:
            print(r.get('class'))
except Exception as e:
    print('ERROR', str(e))
