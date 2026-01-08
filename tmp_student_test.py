import json
from models.student import StudentManager

def run_test():
    data = {
        'student_code': '',
        'first_name': 'Testy',
        'last_name': 'Dup',
        'class_name': 'Grade 1',
        'birth_date': '2018-01-01',
        'parent_name': 'Parent One',
        'parent_phone': '0712345678',
        'parent_email': 'parent@example.local',
        'address': '123 Main St',
        'enrollment_date': '2024-01-01',
        'is_active': True
    }

    try:
        success, message, student = StudentManager.create_student(data)
        out1 = {'success': success, 'message': message, 'student_id': student.student_id if student else None}
        print(json.dumps(out1))

        # Attempt to create duplicate
        success2, message2, student2 = StudentManager.create_student(data)
        out2 = {'success': success2, 'message': message2, 'student_id': student2.student_id if student2 else None}
        print(json.dumps(out2))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))

if __name__ == '__main__':
    run_test()
