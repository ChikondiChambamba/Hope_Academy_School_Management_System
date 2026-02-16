import json
from models.teacher import TeacherManager

def run_test():
    data = {
        'teacher_code': '',
        'first_name': 'AutoTest',
        'last_name': 'Runner',
        'phone': '0712345678',
        'email': 'autotest@example.local',
        'subject_specialization': 'Testing',
        'hire_date': '2025-01-01',
        'is_active': True
    }

    try:
        success, message, teacher = TeacherManager.create_teacher(data)
        out = {
            'success': success,
            'message': message,
            'teacher_id': teacher.teacher_id if teacher else None
        }
    except Exception as e:
        out = {'success': False, 'message': str(e), 'teacher_id': None}

    print(json.dumps(out))

if __name__ == '__main__':
    run_test()
