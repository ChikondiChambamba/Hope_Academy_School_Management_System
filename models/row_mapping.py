"""Build model dataclasses from query rows.

Queries often join extra columns (a student's first/last name, class, ...).
Passing a row straight to `cls(**row)` raises TypeError for any column the
dataclass does not declare, which callers then swallowed as "no results".
"""
from dataclasses import fields
from typing import Any, Dict, Type, TypeVar

T = TypeVar("T")


def from_row(cls: Type[T], row: Dict[str, Any]) -> T:
    data = dict(row)
    names = {f.name for f in fields(cls)}
    if "student_name" in names and "student_name" not in data and ("first_name" in data or "last_name" in data):
        if "first_name" not in names:   # joined student columns, not the model's own
            data["student_name"] = f"{data.get('first_name') or ''} {data.get('last_name') or ''}".strip()
    if "class_name" in names and "class_name" not in data and "class" in data:
        data["class_name"] = data["class"]
    return cls(**{k: v for k, v in data.items() if k in names})
