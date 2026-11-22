"""Compatibility package for financial_reports.

This makes `reports.generators.financial_reports` importable while
keeping the existing implementation in `financial_report.py`.
"""
from ..financial_report import (
    build_student_fees_report_data,
    generate_fee_collection_report,
    generate_expense_report,
    generate_financial_summary_report,
    generate_student_fees_report,
    generate_salary_report,
)

__all__ = [
    'build_student_fees_report_data',
    'generate_fee_collection_report',
    'generate_expense_report',
    'generate_financial_summary_report',
    'generate_student_fees_report',
    'generate_salary_report',
]
