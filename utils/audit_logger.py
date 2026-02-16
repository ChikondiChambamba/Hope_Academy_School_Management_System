"""
Audit logging module for tracking user actions and system changes.
This module provides comprehensive audit trail functionality for compliance and security.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import json
from pathlib import Path

import config
from database.connection import db


class AuditAction(Enum):
    """Types of audit actions."""
    # Student actions
    STUDENT_CREATED = "STUDENT_CREATED"
    STUDENT_UPDATED = "STUDENT_UPDATED"
    STUDENT_DELETED = "STUDENT_DELETED"
    STUDENT_DEACTIVATED = "STUDENT_DEACTIVATED"
    
    # Finance actions
    PAYMENT_RECORDED = "PAYMENT_RECORDED"
    PAYMENT_DELETED = "PAYMENT_DELETED"
    EXPENSE_RECORDED = "EXPENSE_RECORDED"
    EXPENSE_DELETED = "EXPENSE_DELETED"
    FEE_TYPE_CREATED = "FEE_TYPE_CREATED"
    FEE_TYPE_UPDATED = "FEE_TYPE_UPDATED"
    
    # Teacher actions
    TEACHER_CREATED = "TEACHER_CREATED"
    TEACHER_UPDATED = "TEACHER_UPDATED"
    TEACHER_DELETED = "TEACHER_DELETED"
    TEACHER_SALARY_UPDATED = "TEACHER_SALARY_UPDATED"
    
    # Attendance actions
    ATTENDANCE_RECORDED = "ATTENDANCE_RECORDED"
    ATTENDANCE_UPDATED = "ATTENDANCE_UPDATED"
    
    # Inventory actions
    INVENTORY_ITEM_CREATED = "INVENTORY_ITEM_CREATED"
    INVENTORY_ITEM_UPDATED = "INVENTORY_ITEM_UPDATED"
    INVENTORY_ITEM_DELETED = "INVENTORY_ITEM_DELETED"
    
    # User actions
    USER_LOGIN = "USER_LOGIN"
    USER_LOGOUT = "USER_LOGOUT"
    USER_CREATED = "USER_CREATED"
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    
    # System actions
    DATABASE_BACKUP = "DATABASE_BACKUP"
    DATABASE_RESTORE = "DATABASE_RESTORE"
    DATA_EXPORTED = "DATA_EXPORTED"
    DATA_IMPORTED = "DATA_IMPORTED"
    SETTINGS_CHANGED = "SETTINGS_CHANGED"


class AuditLogger:
    """Centralized audit logging system."""
    
    def __init__(self):
        """Initialize audit logger."""
        self.logger = logging.getLogger('audit')
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup audit logger with file handler."""
        log_dir = Path(config.Config.PATHS.get('data', config.Config.BASE_DIR / 'data')) / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        audit_log_file = log_dir / 'audit.log'
        
        handler = logging.FileHandler(audit_log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_action(
        self,
        action: AuditAction,
        user: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
        error_message: Optional[str] = None
    ) -> bool:
        """
        Log an audit action to database and file.
        
        Args:
            action: Type of action performed
            user: Username of user performing action
            entity_type: Type of entity affected (Student, Payment, etc)
            entity_id: ID of entity affected
            details: Additional details as dictionary
            status: SUCCESS or FAILURE
            error_message: Error details if status is FAILURE
        
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            # Get current user if not specified
            if not user:
                user = getattr(config.Config, 'CURRENT_USER', 'System')
            
            # Build audit record
            audit_record = {
                'timestamp': datetime.now().isoformat(),
                'action': action.value,
                'user': user,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'status': status,
                'details': json.dumps(details) if details else None,
                'error_message': error_message,
                'ip_address': '127.0.0.1'  # TODO: Get actual IP for network apps
            }
            
            # Insert into database
            query = """
                INSERT INTO audit_log 
                (timestamp, action, user, entity_type, entity_id, status, details, error_message, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                audit_record['timestamp'],
                audit_record['action'],
                audit_record['user'],
                audit_record['entity_type'],
                audit_record['entity_id'],
                audit_record['status'],
                audit_record['details'],
                audit_record['error_message'],
                audit_record['ip_address']
            )
            
            db.execute_query(query, params)
            
            # Also log to file
            log_message = f"[{action.value}] User: {user}, Entity: {entity_type} (ID: {entity_id}), Status: {status}"
            if error_message:
                log_message += f", Error: {error_message}"
            
            self.logger.info(log_message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log audit action: {str(e)}")
            return False
    
    def get_user_actions(
        self,
        user: str,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Get audit actions for specific user."""
        try:
            query = """
                SELECT * FROM audit_log
                WHERE user = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """
            results = db.execute_query(query, (user, limit, offset), fetch=True)
            return results if results else []
        except Exception as e:
            logging.error(f"Error retrieving user actions: {str(e)}")
            return []
    
    def get_entity_history(
        self,
        entity_type: str,
        entity_id: Any,
        limit: int = 50
    ) -> list:
        """Get action history for specific entity."""
        try:
            query = """
                SELECT * FROM audit_log
                WHERE entity_type = %s AND entity_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            results = db.execute_query(query, (entity_type, entity_id, limit), fetch=True)
            return results if results else []
        except Exception as e:
            logging.error(f"Error retrieving entity history: {str(e)}")
            return []
    
    def get_action_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary of audit actions in date range."""
        try:
            where_clause = "1=1"
            params = []
            
            if start_date:
                where_clause += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                where_clause += " AND timestamp <= %s"
                params.append(end_date)
            
            query = f"""
                SELECT action, COUNT(*) as count
                FROM audit_log
                WHERE {where_clause}
                GROUP BY action
                ORDER BY count DESC
            """
            
            results = db.execute_query(query, tuple(params), fetch=True)
            
            summary = {}
            for row in (results or []):
                summary[row['action']] = row['count']
            
            return summary
            
        except Exception as e:
            logging.error(f"Error retrieving audit summary: {str(e)}")
            return {}


# Global audit logger instance
audit_logger = AuditLogger()


def log_student_action(
    action: AuditAction,
    student_id: int,
    details: Optional[Dict] = None,
    error: Optional[str] = None
) -> bool:
    """Log student-related action."""
    return audit_logger.log_action(
        action=action,
        entity_type='Student',
        entity_id=student_id,
        details=details,
        status='FAILURE' if error else 'SUCCESS',
        error_message=error
    )


def log_payment_action(
    action: AuditAction,
    payment_id: int,
    student_id: int,
    amount: float,
    details: Optional[Dict] = None,
    error: Optional[str] = None
) -> bool:
    """Log payment-related action."""
    return audit_logger.log_action(
        action=action,
        entity_type='Payment',
        entity_id=payment_id,
        details={
            'student_id': student_id,
            'amount': amount,
            **(details or {})
        },
        status='FAILURE' if error else 'SUCCESS',
        error_message=error
    )


def log_teacher_action(
    action: AuditAction,
    teacher_id: int,
    details: Optional[Dict] = None,
    error: Optional[str] = None
) -> bool:
    """Log teacher-related action."""
    return audit_logger.log_action(
        action=action,
        entity_type='Teacher',
        entity_id=teacher_id,
        details=details,
        status='FAILURE' if error else 'SUCCESS',
        error_message=error
    )


def log_user_action(
    action: AuditAction,
    username: str,
    details: Optional[Dict] = None
) -> bool:
    """Log user-related action."""
    return audit_logger.log_action(
        action=action,
        user=username,
        entity_type='User',
        entity_id=username,
        details=details
    )


def log_system_action(
    action: AuditAction,
    details: Optional[Dict] = None,
    error: Optional[str] = None
) -> bool:
    """Log system-related action."""
    return audit_logger.log_action(
        action=action,
        entity_type='System',
        details=details,
        status='FAILURE' if error else 'SUCCESS',
        error_message=error
    )
