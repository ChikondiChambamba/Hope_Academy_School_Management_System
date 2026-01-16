import sys
import os

# Ensure project root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.connection import db
import config

classes = ['Nursery', 'Reception', 'Grade 1', 'Grade 2', 'Grade 3']
try:
    for cname in classes:
        try:
            db.execute_query('INSERT INTO classes (class_name, academic_year) VALUES (%s, %s)', (cname, config.Config.CURRENT_ACADEMIC_YEAR))
            print('INSERTED', cname)
        except Exception as e:
            print('SKIP', cname, str(e))
    print('DONE')
except Exception as e:
    print('ERROR', str(e))
