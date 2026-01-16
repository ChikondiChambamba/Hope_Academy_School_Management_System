import sys
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.connection import db
import config

sample = ['Nursery','Reception','Grade 1','Grade 2','Grade 3']
try:
    for name in sample:
        try:
            res = db.execute_query('DELETE FROM classes WHERE class_name=%s AND academic_year=%s', (name, config.Config.CURRENT_ACADEMIC_YEAR))
            print('DELETED', name)
        except Exception as e:
            print('ERROR', name, str(e))
    print('DONE')
except Exception as e:
    print('ERROR', str(e))
