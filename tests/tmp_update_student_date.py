import json
from models.student import StudentManager

# Update example student id (adjust ID if needed)
student_id = 32
res = StudentManager.update_student(student_id, {'parent_name': 'Mr Kapesi', 'parent_phone': '0123456789', 'enrollment_date': '2024-02-01'})
print(json.dumps({'result': res}))
