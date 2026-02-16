import json
from models.student import StudentManager

student_id = 32
res = StudentManager.delete_student(student_id)
print(json.dumps({'result': res}))
