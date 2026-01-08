import json
from models.teacher import TeacherManager

# Update example teacher
res = TeacherManager.update_teacher(2, {'hire_date': '2026-01-01', 'first_name': 'chikondi'})
print(json.dumps({'result': res}))
