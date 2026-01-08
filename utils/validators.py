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
        # Accept numbers with optional + and country code
        phone = phone.strip()
        # Allow +265 prefix specifically
        if phone.startswith('+'):
            # remove spaces and dashes but keep leading +
            cleaned = '+' + re.sub(r'[\s\-\(\)]', '', phone[1:])
            if cleaned.startswith('+265'):
                digits = re.sub(r'\D', '', cleaned[4:])
                return digits.isdigit() and 6 <= len(digits) <= 10
            else:
                # allow other international formats
                digits = re.sub(r'\D', '', cleaned[1:])
                return digits.isdigit() and 7 <= len(digits) <= 15
        else:
            cleaned = re.sub(r'[\s\-\(\)+]', '', phone)
            return cleaned.isdigit() and 6 <= len(cleaned) <= 15
