"""
Database package for School Management System
"""
from .connection import db, DatabaseConnection

__all__ = ['db', 'DatabaseConnection']