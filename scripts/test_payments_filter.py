import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from database.connection import db

cases = [
    {'fee_filter': None, 'student_filter': None},
    {'fee_filter': 1, 'student_filter': None},
    {'fee_filter': None, 'student_filter': 1},
    {'fee_filter': 1, 'student_filter': 2},
]
for c in cases:
    fee_filter = c['fee_filter']
    student_filter = c['student_filter']
    where_clauses = []
    params = []
    if fee_filter:
        where_clauses.append('sf.fee_type_id = %s')
        params.append(fee_filter)
    if student_filter:
        where_clauses.append('sf.student_id = %s')
        params.append(student_filter)
    where_sql = ''
    if where_clauses:
        where_sql = 'WHERE ' + ' AND '.join(where_clauses)
    query = f"""
        SELECT sf.fee_id FROM student_fees sf
        {where_sql}
    """
    try:
        print('Running with params', params)
        res = db.execute_query(query, tuple(params) if params else None, fetch=True)
        print('OK, returned', len(res))
    except Exception as e:
        print('ERROR', e)
