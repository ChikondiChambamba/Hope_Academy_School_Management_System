"""Validation helpers (compat shim expected by models)"""
import re

class Validators:
    @staticmethod
    def validate_email(email: str) -> bool:
        if not email:
            return True
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        if not phone:
            return True
        # Remove spaces and common punctuation
        cleaned = re.sub(r'[\s\-\(\)+]', '', phone)
        return cleaned.isdigit() and 7 <= len(cleaned) <= 15
