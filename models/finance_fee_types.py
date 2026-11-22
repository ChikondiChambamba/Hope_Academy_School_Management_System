"""Fee type model and helpers."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import config
from database.connection import db
from database.queries import Queries

@dataclass
class FeeType:
    """Fee type model"""
    
    fee_type_id: Optional[int] = None
    fee_name: str = ""
    description: str = ""
    amount: float = 0.0
    term: str = ""
    academic_year: str = ""
    is_required: bool = True
    created_at: Optional[datetime] = None

    CARRIED_FORWARD_FEE_NAME = "Carried Forward Fee Balance"

    @staticmethod
    def is_carried_forward_fee_name(fee_name: str) -> bool:
        return (fee_name or "").strip().lower() == FeeType.CARRIED_FORWARD_FEE_NAME.lower()

    @staticmethod
    def ensure_term_labels() -> None:
        """Normalize legacy fee type term labels like '2' into canonical labels like 'Term 2'.

        A one-off cleanup of old data: it runs once per session, not before every query.
        """
        if not db.once('fee_types.term_labels'):
            return
        try:
            for canonical in getattr(config.Config, 'TERMS', []) or []:
                canonical_name = config.Config.normalize_term_name(canonical)
                for alias in config.Config.get_term_aliases(canonical_name):
                    if alias and alias != canonical_name:
                        db.execute_query(
                            "UPDATE fee_types SET term = %s WHERE TRIM(term) = %s",
                            (canonical_name, alias)
                        )
        except Exception:
            pass

    @staticmethod
    def ensure_carried_forward_fee_type(academic_year: str = None, term: str = None) -> Optional[int]:
        """Ensure the carried-forward balance exists as one normal fee type for the term."""
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        term = config.Config.normalize_term_name(term or config.Config.CURRENT_TERM)
        try:
            FeeType.ensure_term_labels()
            existing = db.execute_query(
                """
                SELECT fee_type_id
                FROM fee_types
                WHERE academic_year = %s
                  AND term = %s
                  AND LOWER(TRIM(fee_name)) = LOWER(%s)
                ORDER BY fee_type_id
                LIMIT 1
                """,
                (academic_year, term, FeeType.CARRIED_FORWARD_FEE_NAME),
                fetch=True
            ) or []
            if existing:
                return int(existing[0]['fee_type_id'])
            return db.execute_query(
                """
                INSERT INTO fee_types (fee_name, description, amount, term, academic_year, is_required)
                VALUES (%s, %s, 0, %s, %s, 1)
                """,
                (
                    FeeType.CARRIED_FORWARD_FEE_NAME,
                    "Student-specific balance carried forward from the previous term.",
                    term,
                    academic_year
                )
            )
        except Exception:
            return None
    
    def validate(self) -> tuple[bool, str]:
        """Validate fee type data"""
        if self.term:
            self.term = config.Config.normalize_term_name(self.term)
        if not self.fee_name.strip():
            return False, "Fee name is required"
        
        if self.amount <= 0:
            return False, "Amount must be greater than 0"
        
        if not self.academic_year:
            return False, "Academic year is required"
        
        return True, ""
    
    def save(self) -> tuple[bool, str]:
        """Save fee type to database"""
        is_valid, message = self.validate()
        if not is_valid:
            return False, message
        
        try:
            fee_data = self.to_dict()
            
            if self.fee_type_id:  # Update
                query = """
                    UPDATE fee_types SET 
                    fee_name = %s, description = %s, amount = %s,
                    term = %s, academic_year = %s, is_required = %s
                    WHERE fee_type_id = %s
                """
                params = (
                    fee_data['fee_name'],
                    fee_data['description'],
                    fee_data['amount'],
                    fee_data['term'],
                    fee_data['academic_year'],
                    fee_data['is_required'],
                    self.fee_type_id
                )
                
                db.execute_query(query, params)
                return True, "Fee type updated successfully"
                
            else:  # Insert
                query = """
                    INSERT INTO fee_types 
                    (fee_name, description, amount, term, academic_year, is_required)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                params = (
                    fee_data['fee_name'],
                    fee_data['description'],
                    fee_data['amount'],
                    fee_data['term'],
                    fee_data['academic_year'],
                    fee_data['is_required']
                )
                
                fee_type_id = db.execute_query(query, params)
                self.fee_type_id = fee_type_id
                return True, f"Fee type added successfully with ID: {fee_type_id}"
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert fee type to dictionary"""
        data = asdict(self)
        
        # Convert datetime to string
        if data['created_at'] and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FeeType':
        """Create FeeType instance from a query row (extra joined columns are ignored)."""
        from .row_mapping import from_row
        return from_row(cls, data)
    
    @classmethod
    def get_all(cls, academic_year: str = None) -> List['FeeType']:
        """Get all fee types for academic year"""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        
        try:
            cls.ensure_term_labels()
            cls.ensure_carried_forward_fee_type(academic_year, config.Config.CURRENT_TERM)
            query = Queries.GET_FEE_TYPES
            results = db.execute_query(query, (academic_year,), fetch=True)
            return [cls.from_dict(row) for row in results]
        except:
            return []
    
    @classmethod
    def get_by_id(cls, fee_type_id: int) -> Optional['FeeType']:
        """Get fee type by ID"""
        try:
            cls.ensure_term_labels()
            query = "SELECT * FROM fee_types WHERE fee_type_id = %s"
            result = db.execute_query(query, (fee_type_id,), fetch=True)
            if result:
                return cls.from_dict(result[0])
            return None
        except:
            return None

    @classmethod
    def get_applicable_for_class(cls, class_name: str, academic_year: str = None, term: str = None) -> List['FeeType']:
        """Get fee types applicable to a class (or globally applicable when no class mapping exists)."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        if not term:
            term = config.Config.CURRENT_TERM
        term = config.Config.normalize_term_name(term)
        term_aliases = config.Config.get_term_aliases(term) or [term]
        term_placeholders = ", ".join(["%s"] * len(term_aliases))
        class_name = (class_name or "").strip()
        if not class_name:
            return cls.get_all(academic_year)
        try:
            cls.ensure_term_labels()
            cls.ensure_carried_forward_fee_type(academic_year, term)
            query = """
                SELECT ft.*
                FROM fee_types ft
                WHERE ft.academic_year = %s
                  AND (
                        ft.term IN ({term_placeholders})
                        OR ft.term IS NULL
                        OR ft.term = ''
                        OR NOT EXISTS (
                            SELECT 1
                            FROM fee_types ftx
                            WHERE ftx.academic_year = %s
                              AND ftx.term IN ({term_placeholders})
                        )
                  )
                  AND (
                        NOT EXISTS (
                            SELECT 1 FROM fee_type_classes ftc0
                            WHERE ftc0.fee_type_id = ft.fee_type_id
                        )
                        OR EXISTS (
                            SELECT 1
                            FROM fee_type_classes ftc
                            JOIN classes c ON c.class_id = ftc.class_id
                            WHERE ftc.fee_type_id = ft.fee_type_id
                              AND LOWER(c.class_name) = LOWER(%s)
                              AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                        )
                  )
                ORDER BY ft.fee_name
            """.format(term_placeholders=term_placeholders)
            params = tuple([academic_year] + term_aliases + [academic_year] + term_aliases + [class_name, academic_year])
            results = db.execute_query(query, params, fetch=True)
            return [cls.from_dict(row) for row in (results or [])]
        except Exception:
            # Fallback to previous behavior if mapping table is unavailable
            return cls.get_all(academic_year)

    @classmethod
    def is_applicable_to_class(cls, fee_type_id: int, class_name: str, academic_year: str = None) -> bool:
        """Return True if fee type is applicable to the given class."""
        if not academic_year:
            academic_year = config.Config.CURRENT_ACADEMIC_YEAR
        class_name = (class_name or "").strip()
        if not fee_type_id:
            return False
        if not class_name:
            return True
        try:
            query = """
                SELECT
                    CASE
                        WHEN NOT EXISTS (
                            SELECT 1 FROM fee_type_classes ftc0
                            WHERE ftc0.fee_type_id = %s
                        ) THEN 1
                        WHEN EXISTS (
                            SELECT 1
                            FROM fee_type_classes ftc
                            JOIN classes c ON c.class_id = ftc.class_id
                            WHERE ftc.fee_type_id = %s
                              AND LOWER(c.class_name) = LOWER(%s)
                              AND (ftc.academic_year IS NULL OR ftc.academic_year = '' OR ftc.academic_year = %s)
                        ) THEN 1
                        ELSE 0
                    END AS allowed
            """
            res = db.execute_query(query, (fee_type_id, fee_type_id, class_name, academic_year), fetch=True)
            return bool(res and int(res[0].get('allowed') or 0) == 1)
        except Exception:
            # Fallback to permissive behavior to avoid hard failures on old DBs
            return True


