"""
Enhanced error handling and exception management module.
Provides custom exceptions and centralized error handling.
"""

import logging
import traceback
from typing import Optional, Callable, Any
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)


# Custom Exceptions

class SchoolManagementException(Exception):
    """Base exception for all application errors."""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        """
        Initialize exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
        """
        self.message = message
        self.error_code = error_code
        self.timestamp = datetime.now()
        super().__init__(self.message)
    
    def to_dict(self):
        """Convert exception to dictionary."""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'timestamp': self.timestamp.isoformat()
        }


class DatabaseException(SchoolManagementException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, error_code: str = "DB_ERROR"):
        super().__init__(message, error_code)


class ValidationException(SchoolManagementException):
    """Raised when validation fails."""
    
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(message, error_code)


class AuthenticationException(SchoolManagementException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, error_code: str = "AUTH_ERROR"):
        super().__init__(message, error_code)


class AuthorizationException(SchoolManagementException):
    """Raised when user lacks required permissions."""
    
    def __init__(self, message: str, error_code: str = "AUTHZ_ERROR"):
        super().__init__(message, error_code)


class ConfigurationException(SchoolManagementException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, error_code: str = "CONFIG_ERROR"):
        super().__init__(message, error_code)


class DataImportException(SchoolManagementException):
    """Raised when data import fails."""
    
    def __init__(self, message: str, error_code: str = "IMPORT_ERROR", details: Optional[dict] = None):
        super().__init__(message, error_code)
        self.details = details or {}


class FileOperationException(SchoolManagementException):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, error_code: str = "FILE_ERROR"):
        super().__init__(message, error_code)


# Error Handlers

class ErrorHandler:
    """Centralized error handling utility."""
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        context: Optional[str] = None,
        log_traceback: bool = True
    ) -> tuple[bool, str]:
        """
        Handle and log an exception.
        
        Args:
            exception: The exception to handle
            context: Context description for logging
            log_traceback: Whether to log full traceback
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        
        if isinstance(exception, SchoolManagementException):
            message = exception.message
            error_code = exception.error_code
        else:
            message = str(exception)
            error_code = "UNEXPECTED_ERROR"
        
        # Build log message
        log_msg = f"[{error_code}] {message}"
        if context:
            log_msg = f"[{context}] {log_msg}"
        
        # Log error
        logger.error(log_msg)
        
        if log_traceback:
            logger.error(traceback.format_exc())
        
        return False, message
    
    @staticmethod
    def get_user_friendly_message(exception: Exception) -> str:
        """
        Get user-friendly error message.
        
        Args:
            exception: The exception
        
        Returns:
            User-friendly message string
        """
        
        if isinstance(exception, ValidationException):
            return f"Invalid input: {exception.message}"
        elif isinstance(exception, AuthenticationException):
            return "Authentication failed. Please check your credentials."
        elif isinstance(exception, AuthorizationException):
            return "You don't have permission to perform this action."
        elif isinstance(exception, DatabaseException):
            return "A database error occurred. Please try again or contact support."
        elif isinstance(exception, FileOperationException):
            return f"File operation failed: {exception.message}"
        elif isinstance(exception, ConfigurationException):
            return "Application configuration error. Please contact administrator."
        else:
            return "An unexpected error occurred. Please contact support."


# Decorators

def handle_errors(
    default_return: Any = (False, "An error occurred"),
    context: Optional[str] = None,
    log_traceback: bool = True
):
    """
    Decorator to handle exceptions in functions.
    
    Args:
        default_return: Return value on error
        context: Context description
        log_traceback: Whether to log traceback
    
    Example:
        @handle_errors(default_return=(False, "Operation failed"))
        def save_student(student):
            # Function implementation
            pass
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                success, message = ErrorHandler.handle_exception(
                    e,
                    context=context or func.__name__,
                    log_traceback=log_traceback
                )
                
                if isinstance(default_return, tuple):
                    return (success, message)
                else:
                    return default_return
        
        return wrapper
    
    return decorator


def validate_input(**validators):
    """
    Decorator to validate function arguments.
    
    Args:
        **validators: Mapping of argument name to validation function
    
    Example:
        @validate_input(
            email=lambda x: '@' in x,
            age=lambda x: 0 < x < 150
        )
        def create_account(email, age):
            pass
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate kwargs
            for arg_name, validator in validators.items():
                if arg_name in kwargs:
                    value = kwargs[arg_name]
                    if not validator(value):
                        raise ValidationException(
                            f"Invalid value for {arg_name}: {value}",
                            "VALIDATION_ERROR"
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_permission(feature: str):
    """
    Decorator to check user permissions.
    
    Args:
        feature: Feature name to check permission for
    
    Example:
        @require_permission('finance')
        def record_payment():
            pass
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import config
            if not config.Config.has_permission(feature):
                raise AuthorizationException(
                    f"You don't have permission to access {feature}",
                    "INSUFFICIENT_PERMISSION"
                )
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry function on failure.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for delay after each attempt
    
    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        def connect_to_database():
            pass
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    
                    if attempt >= max_attempts:
                        logger.error(f"Max retry attempts ({max_attempts}) exceeded for {func.__name__}")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt} failed for {func.__name__}. "
                        f"Retrying in {current_delay}s... ({max_attempts - attempt} attempts left)"
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    
    return decorator


# Context Managers

class ErrorContext:
    """Context manager for error handling."""
    
    def __init__(self, context_name: str, critical: bool = False):
        """
        Initialize error context.
        
        Args:
            context_name: Description of the context
            critical: If True, reraise exceptions
        """
        self.context_name = context_name
        self.critical = critical
        self.error: Optional[Exception] = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            
            logger.error(
                f"Error in {self.context_name}: {exc_val}",
                exc_info=True
            )
            
            if self.critical:
                return False  # Reraise exception
            else:
                return True   # Suppress exception


# Exception Handler Registry

class ExceptionRegistry:
    """Registry for handling specific exception types."""
    
    _handlers = {}
    
    @classmethod
    def register_handler(cls, exception_type: type, handler: Callable):
        """Register handler for exception type."""
        cls._handlers[exception_type] = handler
    
    @classmethod
    def handle(cls, exception: Exception) -> tuple[bool, str]:
        """Handle exception using registered handler."""
        handler = cls._handlers.get(type(exception))
        if handler:
            return handler(exception)
        else:
            return ErrorHandler.handle_exception(exception)


# Register default handlers
def _register_default_handlers():
    """Register default exception handlers."""
    
    def handle_db_exception(e: DatabaseException) -> tuple[bool, str]:
        return False, f"Database error: {e.message}"
    
    def handle_validation_exception(e: ValidationException) -> tuple[bool, str]:
        return False, f"Validation failed: {e.message}"
    
    ExceptionRegistry.register_handler(DatabaseException, handle_db_exception)
    ExceptionRegistry.register_handler(ValidationException, handle_validation_exception)


_register_default_handlers()
