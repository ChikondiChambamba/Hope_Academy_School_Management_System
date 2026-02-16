"""
Feature Integration Guide

This guide documents how the new features (audit logging, error handling, email notifications)
are integrated into the School Management System and how to extend them.
"""

# Feature Integration Guide

## Overview

Three new feature modules have been integrated into the School Management System:

1. **Audit Logging** - Track all user actions for compliance and security
2. **Error Handling** - Centralized exception management and user-friendly error messages
3. **Email Notifications** - Automated parent communication and announcements

---

## 1. Audit Logging Integration

### Current Integration Points

#### Student Management
- **File**: [models/student.py](models/student.py)
- **Methods**: `Student.save()`
- **Actions Logged**: CREATE, UPDATE
- **Status**: ✓ Implemented

```python
from utils.audit_logger import log_student_action

# When saving a student
log_student_action('CREATE', student_id, 'Student added', status='SUCCESS')
log_student_action('UPDATE', student_id, 'Student updated', status='SUCCESS')
```

#### Finance Management
- **File**: [models/finance.py](models/finance.py)
- **Methods**: `FeePayment.save()`, `FeePayment.update()`
- **Actions Logged**: CREATE (payment recorded), UPDATE (payment modified), FAILED
- **Status**: ✓ Implemented

```python
from utils.audit_logger import log_payment_action

# When recording a payment
log_payment_action('CREATE', fee_id, 'Payment recorded for student', details={
    'receipt_number': receipt_number,
    'amount': amount,
    'method': payment_method
})
```

### Available Helper Functions

```python
from utils.audit_logger import (
    log_student_action,        # Log student-related actions
    log_payment_action,        # Log finance-related actions
    log_teacher_action,        # Log teacher-related actions
    log_user_action,           # Log user management actions
    log_system_action          # Log system-level actions
)

# Example usage
log_student_action(action, entity_id, description, details=None, status='SUCCESS')
log_payment_action(action, entity_id, description, details=None, status='SUCCESS')
```

### Viewing Audit Logs

Access audit logs through the UI:
1. Open Application
2. Go to **Tools → View Audit Log**
3. Search and filter by user, action, or date range
4. Export to CSV for reporting

---

## 2. Error Handling Integration

### Current Integration Points

#### Error Decorators
- **File**: [utils/error_handler.py](utils/error_handler.py)
- **Usage**: Applied to functions that need error handling

```python
from utils.error_handler import handle_errors, validate_input, retry

@handle_errors
def process_student_data(data):
    # Function automatically catches and logs errors
    pass

@validate_input(['name', 'email'])
def create_user(name, email, password):
    # Validates required fields before execution
    pass

@retry(max_attempts=3, backoff=2)
def fetch_from_api():
    # Automatically retries on failure with exponential backoff
    pass
```

#### Exception Handling
```python
from utils.error_handler import StudentNotFoundError, DatabaseError, ValidationError

try:
    student = Student.get(student_id)
except StudentNotFoundError:
    messagebox.showerror('Error', 'Student not found')
except ValidationError as e:
    messagebox.showerror('Validation Error', str(e))
except DatabaseError as e:
    messagebox.showerror('Database Error', 'Failed to access database')
```

### Custom Exceptions Available

1. **StudentNotFoundError** - Student record not found
2. **TeacherNotFoundError** - Teacher record not found
3. **PaymentNotFoundError** - Payment record not found
4. **DatabaseError** - Database operation failed
5. **ValidationError** - Input validation failed
6. **PermissionError** - User lacks required permission
7. **ConfigurationError** - Configuration issue detected
8. **EmailError** - Email sending failed

---

## 3. Email Notification Integration

### Configuration

First, configure email settings through the UI:
1. **Tools → Email Configuration**
2. Enter SMTP server details
3. Enter sender credentials
4. Test connection
5. Click OK to save

Alternatively, edit [config.py](config.py):

```python
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'noreply@hopeacademy.com',
    'sender_name': 'Hope Academy',
    'username': 'your_email@gmail.com',
    'password': 'your_app_password',
    'use_tls': True
}
```

### Email Templates Available

```python
from utils.email_notifier import EmailNotifier, EmailConfig, EmailTemplate

notifier = EmailNotifier(email_config)

# Payment Reminder
notifier.send_payment_reminder(
    parent_email='parent@email.com',
    student_name='John Doe',
    amount_due=5000,
    due_date='2026-02-01'
)

# Payment Confirmation
notifier.send_payment_confirmation(
    parent_email='parent@email.com',
    student_name='John Doe',
    amount_paid=5000,
    receipt_number='REC-20260109-0001'
)

# Attendance Alert
notifier.send_attendance_alert(
    parent_email='parent@email.com',
    student_name='John Doe',
    absences=3,
    alert_message='Your child has 3 unexcused absences'
)

# Fee Exemption Notification
notifier.send_fee_exemption_notification(
    parent_email='parent@email.com',
    student_name='John Doe',
    fee_type='School Levies',
    reason='Approved exemption'
)

# General Announcement
notifier.send_announcement(
    parent_email='parent@email.com',
    title='School Holiday Notification',
    message='School will be closed on...'
)
```

### Bulk Email Sending

```python
# Send bulk emails
emails = [
    {'email': 'parent1@email.com', 'student': 'Student 1', 'amount': 5000},
    {'email': 'parent2@email.com', 'student': 'Student 2', 'amount': 5500},
]

notifier.send_bulk_emails(
    emails=emails,
    template='payment_reminder'
)
```

---

## Integration Checklist

### Phase 1: Foundation (Completed ✓)
- [x] Audit logging system implemented
- [x] Error handling system implemented
- [x] Email notification system implemented
- [x] Database schema updated with audit_log table
- [x] UI dialogs created for audit viewing and email config

### Phase 2: Core Integration (In Progress)
- [x] Student save operations log audit trail
- [x] Payment operations log audit trail
- [ ] Teacher operations log audit trail
- [ ] Attendance operations log audit trail
- [ ] Inventory operations log audit trail

### Phase 3: Email Integration
- [ ] Send payment confirmation emails on payment record
- [ ] Send payment reminder emails for overdue payments
- [ ] Send attendance alerts for excessive absences
- [ ] Send fee exemption notifications
- [ ] Send bulk announcement emails

### Phase 4: Advanced Features
- [ ] Email scheduling for reminders
- [ ] SMS notifications (future)
- [ ] Automated backup notifications
- [ ] Daily/weekly digest emails
- [ ] Custom email templates

---

## Database Migration

### For Existing Installations

Run the migration script to add the audit_log table:

```bash
python scripts/migrate_audit_log.py
```

This script will:
1. Create a database backup
2. Add the audit_log table if it doesn't exist
3. Create necessary indexes
4. Verify the migration was successful

### For New Installations

The audit_log table is automatically created when running:

```bash
python setup_database.py
```

---

## Extending the Features

### Adding Audit Logging to New Operations

```python
from utils.audit_logger import AuditLogger

logger = AuditLogger()

# Log a custom action
logger.log_action(
    action='DELETE',
    user='admin@hopeacademy.com',
    entity_type='inventory_item',
    entity_id=123,
    status='SUCCESS',
    details={'quantity': 50, 'reason': 'Stock damaged'}
)

# Retrieve action history
history = logger.get_entity_history('student', student_id=42)
for record in history:
    print(f"{record['timestamp']}: {record['action']} by {record['user']}")
```

### Adding Custom Error Handling

```python
from utils.error_handler import ErrorHandler, CustomException

# Define custom exception
class InventoryError(CustomException):
    """Raised when inventory operation fails"""
    pass

# Use in your code
@handle_errors
def update_inventory(item_id, quantity):
    if quantity < 0:
        raise InventoryError('Quantity cannot be negative')
    # ... update logic
```

### Sending Custom Emails

```python
from utils.email_notifier import EmailNotifier, EmailConfig

email_config = EmailConfig(
    smtp_server='smtp.gmail.com',
    smtp_port=587,
    sender_email='noreply@hopeacademy.com',
    sender_name='Hope Academy',
    username='your_email@gmail.com',
    password='your_password',
    use_tls=True
)

notifier = EmailNotifier(email_config)

# Send custom email
notifier.send_email(
    to='parent@email.com',
    subject='Custom Notification',
    body='<html><body>Custom HTML email content</body></html>',
    is_html=True
)
```

---

## Testing the Features

### Test Audit Logging

```python
# Add a student and verify audit log
student = Student(first_name='Test', last_name='Student', class_name='Class A')
student.save()

# Check audit logs
from utils.audit_logger import AuditLogger
logger = AuditLogger()
logs = logger.get_user_actions('admin@hopeacademy.com', limit=10)
print(logs)  # Should show the CREATE action
```

### Test Email Notifications

```python
# Verify email configuration
from utils.email_notifier import EmailNotifier, EmailConfig
from config import EMAIL_CONFIG

notifier = EmailNotifier(EMAIL_CONFIG)
if notifier.test_connection():
    print("✓ Email configuration is valid")
else:
    print("✗ Email configuration failed")
```

### Test Error Handling

```python
# Test error handling decorator
from utils.error_handler import handle_errors

@handle_errors
def test_error_handling():
    raise Exception("Test error")

result = test_error_handling()
# Should catch exception and return user-friendly message
```

---

## Troubleshooting

### Audit Logging Not Working

1. **Check if audit_log table exists**:
   ```sql
   SHOW TABLES LIKE 'audit_log';
   ```

2. **If not found, run migration**:
   ```bash
   python scripts/migrate_audit_log.py
   ```

3. **Verify database connection** in config.py

### Email Not Sending

1. **Test email configuration**:
   - Go to Tools → Email Configuration
   - Click "Test Connection"

2. **Check SMTP credentials**:
   - Verify server name, port, username, password
   - For Gmail, use "App Passwords" not regular password

3. **Check email logs**:
   - Review data/migration_logs.txt for details

### Missing Audit Records

1. **Verify user is logged in** (audit needs current user)
2. **Check database permissions** for audit_log table
3. **Restart application** after migrations

---

## Performance Considerations

### Audit Logging
- Audit logs are written synchronously to database
- Consider archiving old logs (>1 year) periodically
- Indexes ensure fast searches

### Email Notifications
- Use bulk_emails() for sending to multiple recipients
- Configure email scheduler for off-peak times
- Monitor SMTP connection limits

### Error Handling
- Retry decorator uses exponential backoff to avoid overload
- Max retry attempts set to 3 by default (configurable)
- All errors logged to database and file

---

## API Reference

For complete API documentation, see [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

---

## Support

For questions or issues:
1. Check [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)
2. Review [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
3. Contact development team

---

**Last Updated**: January 2026  
**Version**: 1.0.0
