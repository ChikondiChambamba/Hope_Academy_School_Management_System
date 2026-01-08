"""
Expense category model and CRUD helpers
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from database.connection import db


@dataclass
class ExpenseCategory:
    category_id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: Optional[str] = None

    @staticmethod
    def ensure_table():
        """Create table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS expense_categories (
            category_id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        try:
            db.execute_query(query)
        except Exception:
            pass

    @classmethod
    def get_all(cls) -> List['ExpenseCategory']:
        try:
            cls.ensure_table()
            results = db.execute_query("SELECT category_id, name, description, created_at FROM expense_categories ORDER BY name", fetch=True)
            return [cls(category_id=r['category_id'], name=r['name'], description=r.get('description') or '', created_at=str(r.get('created_at'))) for r in results]
        except Exception:
            return []

    def save(self) -> tuple[bool, str]:
        try:
            self.ensure_table()
            if self.category_id:
                query = "UPDATE expense_categories SET name = %s, description = %s WHERE category_id = %s"
                db.execute_query(query, (self.name, self.description, self.category_id))
                return True, "Category updated"
            else:
                query = "INSERT INTO expense_categories (name, description) VALUES (%s, %s)"
                cid = db.execute_query(query, (self.name, self.description))
                self.category_id = cid
                return True, "Category added"
        except Exception as e:
            return False, str(e)

    def delete(self) -> tuple[bool, str]:
        try:
            if not self.category_id:
                return False, "Category id required"
            query = "DELETE FROM expense_categories WHERE category_id = %s"
            db.execute_query(query, (self.category_id,))
            return True, "Category deleted"
        except Exception as e:
            return False, str(e)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
