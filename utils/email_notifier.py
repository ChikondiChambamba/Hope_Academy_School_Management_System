"""
Email notification module for sending emails to parents, staff, and administrators.
Supports configurable email templates and SMTP settings.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class EmailConfig:
    """Email configuration settings."""
    
    # SMTP Configuration
    SMTP_SERVER = "smtp.gmail.com"      # Configure for your email provider
    SMTP_PORT = 587
    SENDER_EMAIL = "noreply@hopeacademy.org"
    SENDER_PASSWORD = ""                # Set via environment variable
    USE_TLS = True
    
    # Email Templates
    TEMPLATES = {
        'payment_reminder': {
            'subject': 'Payment Reminder - {student_name}',
            'body': """
Dear {parent_name},

This is a reminder that {student_name} has an outstanding fee balance of {balance} for {academic_year}.

Fee Details:
- Total Due: {total_due}
- Total Paid: {total_paid}
- Balance: {balance}

Please arrange payment at your earliest convenience.

Regards,
{school_name}
"""
        },
        'payment_confirmation': {
            'subject': 'Payment Confirmation - {student_name}',
            'body': """
Dear {parent_name},

Payment received for {student_name}.

Payment Details:
- Amount: {amount}
- Date: {payment_date}
- Receipt: {receipt_number}
- Fee Type: {fee_type}

New Balance: {new_balance}

Regards,
{school_name}
"""
        },
        'attendance_alert': {
            'subject': 'Low Attendance Alert - {student_name}',
            'body': """
Dear {parent_name},

We are writing to inform you that {student_name} has had low attendance recently.

Attendance Statistics:
- Days Present: {days_present}
- Days Absent: {days_absent}
- Attendance Rate: {attendance_rate}%

Please encourage regular attendance.

Regards,
{school_name}
"""
        },
        'fee_exemption': {
            'subject': 'Fee Exemption Granted - {student_name}',
            'body': """
Dear {parent_name},

A fee exemption has been granted for {student_name}.

Exemption Details:
- Fee Type: {fee_type}
- Reason: {reason}
- Academic Year: {academic_year}

Regards,
{school_name}
"""
        },
        'new_announcement': {
            'subject': 'School Announcement',
            'body': """
Dear {recipient_name},

{announcement_title}

{announcement_content}

For more information, visit the school office.

Regards,
{school_name}
"""
        }
    }


class EmailNotification:
    """Handles sending email notifications."""
    
    def __init__(self):
        """Initialize email notification system."""
        self.config = EmailConfig()
        self.session = None
    
    def connect(self) -> bool:
        """
        Establish SMTP connection.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            self.session = smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT)
            
            if self.config.USE_TLS:
                self.session.starttls()
            
            # Login (only if credentials provided)
            if self.config.SENDER_PASSWORD:
                self.session.login(self.config.SENDER_EMAIL, self.config.SENDER_PASSWORD)
            
            logger.info("SMTP connection established")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP connection failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Email connection error: {str(e)}")
            return False
    
    def disconnect(self):
        """Close SMTP connection."""
        if self.session:
            try:
                self.session.quit()
                logger.info("SMTP connection closed")
            except Exception as e:
                logger.warning(f"Error closing SMTP connection: {str(e)}")
            finally:
                self.session = None
    
    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        html: bool = False,
        attachments: Optional[List[tuple]] = None
    ) -> tuple[bool, str]:
        """
        Send email to recipient.
        
        Args:
            recipient_email: Email address of recipient
            subject: Email subject
            body: Email body content
            html: If True, treat body as HTML
            attachments: List of (filename, file_content) tuples
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.config.SENDER_EMAIL
            message['To'] = recipient_email
            
            # Add body
            mime_type = 'html' if html else 'plain'
            message.attach(MIMEText(body, mime_type))
            
            # Add attachments if provided
            if attachments:
                for filename, content in attachments:
                    part = MIMEText(content)
                    part.add_header('Content-Disposition', 'attachment', filename=filename)
                    message.attach(part)
            
            # Send email
            if not self.session:
                if not self.connect():
                    return False, "Failed to connect to email server"
            
            self.session.send_message(message)
            
            logger.info(f"Email sent to {recipient_email}: {subject}")
            return True, f"Email sent successfully to {recipient_email}"
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending to {recipient_email}: {str(e)}")
            return False, f"SMTP error: {str(e)}"
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            return False, str(e)
    
    def send_payment_reminder(
        self,
        parent_email: str,
        parent_name: str,
        student_name: str,
        balance: float,
        total_due: float,
        total_paid: float,
        academic_year: str
    ) -> tuple[bool, str]:
        """Send payment reminder email."""
        
        template = self.config.TEMPLATES['payment_reminder']
        
        body = template['body'].format(
            parent_name=parent_name,
            student_name=student_name,
            balance=self._format_currency(balance),
            total_due=self._format_currency(total_due),
            total_paid=self._format_currency(total_paid),
            academic_year=academic_year,
            school_name=config.Config.SCHOOL_NAME
        )
        
        subject = template['subject'].format(student_name=student_name)
        
        return self.send_email(parent_email, subject, body)
    
    def send_payment_confirmation(
        self,
        parent_email: str,
        parent_name: str,
        student_name: str,
        amount: float,
        payment_date: str,
        receipt_number: str,
        fee_type: str,
        new_balance: float
    ) -> tuple[bool, str]:
        """Send payment confirmation email."""
        
        template = self.config.TEMPLATES['payment_confirmation']
        
        body = template['body'].format(
            parent_name=parent_name,
            student_name=student_name,
            amount=self._format_currency(amount),
            payment_date=payment_date,
            receipt_number=receipt_number,
            fee_type=fee_type,
            new_balance=self._format_currency(new_balance),
            school_name=config.Config.SCHOOL_NAME
        )
        
        subject = template['subject'].format(student_name=student_name)
        
        return self.send_email(parent_email, subject, body)
    
    def send_attendance_alert(
        self,
        parent_email: str,
        parent_name: str,
        student_name: str,
        days_present: int,
        days_absent: int,
        attendance_rate: float
    ) -> tuple[bool, str]:
        """Send low attendance alert email."""
        
        template = self.config.TEMPLATES['attendance_alert']
        
        body = template['body'].format(
            parent_name=parent_name,
            student_name=student_name,
            days_present=days_present,
            days_absent=days_absent,
            attendance_rate=f"{attendance_rate:.1f}",
            school_name=config.Config.SCHOOL_NAME
        )
        
        subject = template['subject'].format(student_name=student_name)
        
        return self.send_email(parent_email, subject, body)
    
    def send_fee_exemption_notification(
        self,
        parent_email: str,
        parent_name: str,
        student_name: str,
        fee_type: str,
        reason: str,
        academic_year: str
    ) -> tuple[bool, str]:
        """Send fee exemption notification email."""
        
        template = self.config.TEMPLATES['fee_exemption']
        
        body = template['body'].format(
            parent_name=parent_name,
            student_name=student_name,
            fee_type=fee_type,
            reason=reason,
            academic_year=academic_year,
            school_name=config.Config.SCHOOL_NAME
        )
        
        subject = template['subject'].format(student_name=student_name)
        
        return self.send_email(parent_email, subject, body)
    
    def send_announcement(
        self,
        recipient_emails: List[str],
        recipient_name: str,
        announcement_title: str,
        announcement_content: str
    ) -> tuple[int, int]:
        """
        Send announcement to multiple recipients.
        
        Args:
            recipient_emails: List of email addresses
            recipient_name: Name to address recipients as
            announcement_title: Announcement title
            announcement_content: Announcement content
        
        Returns:
            Tuple of (successful_count, failed_count)
        """
        
        template = self.config.TEMPLATES['new_announcement']
        
        body = template['body'].format(
            recipient_name=recipient_name,
            announcement_title=announcement_title,
            announcement_content=announcement_content,
            school_name=config.Config.SCHOOL_NAME
        )
        
        subject = template['subject']
        
        success_count = 0
        failed_count = 0
        
        for email in recipient_emails:
            success, _ = self.send_email(email, subject, body)
            if success:
                success_count += 1
            else:
                failed_count += 1
        
        logger.info(f"Announcement sent: {success_count} successful, {failed_count} failed")
        
        return success_count, failed_count
    
    def send_bulk_emails(
        self,
        recipients: List[Dict[str, Any]],
        template_name: str,
        **template_vars
    ) -> tuple[int, int]:
        """
        Send bulk emails using template.
        
        Args:
            recipients: List of recipient dictionaries with 'email' key
            template_name: Name of email template
            **template_vars: Template variables
        
        Returns:
            Tuple of (successful_count, failed_count)
        """
        
        if template_name not in self.config.TEMPLATES:
            logger.error(f"Template '{template_name}' not found")
            return 0, len(recipients)
        
        template = self.config.TEMPLATES[template_name]
        success_count = 0
        failed_count = 0
        
        for recipient in recipients:
            try:
                email = recipient.get('email')
                if not email:
                    logger.warning("Recipient missing email address")
                    failed_count += 1
                    continue
                
                # Merge recipient data with template variables
                merged_vars = {**recipient, **template_vars}
                
                body = template['body'].format(**merged_vars)
                subject = template['subject'].format(**merged_vars)
                
                success, _ = self.send_email(email, subject, body)
                
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error sending to {recipient.get('email')}: {str(e)}")
                failed_count += 1
        
        return success_count, failed_count
    
    @staticmethod
    def _format_currency(amount: float) -> str:
        """Format amount as currency."""
        symbol = getattr(config.Config, 'CURRENCY_SYMBOL', '$')
        return f"{symbol}{amount:,.2f}"
    
    def test_connection(self) -> bool:
        """Test email configuration and connection."""
        try:
            if not self.connect():
                return False
            self.disconnect()
            return True
        except Exception as e:
            logger.error(f"Email test failed: {str(e)}")
            return False


# Global email notification instance
email_notifier = EmailNotification()


def send_payment_reminder_email(
    student_id: int,
    parent_email: str,
    parent_name: str,
    student_name: str,
    balance: float,
    total_due: float,
    total_paid: float
) -> tuple[bool, str]:
    """Convenience function to send payment reminder."""
    
    academic_year = getattr(config.Config, 'CURRENT_ACADEMIC_YEAR', '2025-2026')
    
    return email_notifier.send_payment_reminder(
        parent_email, parent_name, student_name,
        balance, total_due, total_paid, academic_year
    )


def send_payment_confirmation_email(
    student_id: int,
    parent_email: str,
    parent_name: str,
    student_name: str,
    amount: float,
    payment_date: str,
    receipt_number: str,
    fee_type: str,
    new_balance: float
) -> tuple[bool, str]:
    """Convenience function to send payment confirmation."""
    
    return email_notifier.send_payment_confirmation(
        parent_email, parent_name, student_name,
        amount, payment_date, receipt_number,
        fee_type, new_balance
    )
