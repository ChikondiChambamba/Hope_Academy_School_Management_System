"""Financial summaries and reporting convenience queries."""
from datetime import date, timedelta
from typing import List, Dict, Any
import config
from database.connection import db
from .finance_payments import FeePayment
from .finance_expenses import Expense


class FinanceSummaryMixin:
    @classmethod
    def get_financial_summary(cls, start_date: date = None, end_date: date = None) -> Dict:
        """Get complete financial summary for period"""
        if not start_date:
            start_date = date(date.today().year, 1, 1)
        if not end_date:
            end_date = date.today()
        
        # Get fees collected
        fees_summary = FeePayment.get_total_collected(start_date, end_date)
        
        # Get expenses
        expenses_summary = Expense.get_total_expenses(start_date, end_date)
        
        # Calculate net balance
        total_fees = fees_summary['total_amount']
        total_expenses = expenses_summary['total_amount']
        net_balance = total_fees - total_expenses
        
        # Get student balances
        try:
            balances = cls.get_student_balances(
                config.Config.CURRENT_ACADEMIC_YEAR,
                term=config.Config.CURRENT_TERM
            )
            total_outstanding = sum(float(r.get('balance') or 0) for r in balances if float(r.get('balance') or 0) > 0)
        except:
            total_outstanding = 0
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'revenue': {
                'total_fees': total_fees,
                'payment_count': fees_summary['payment_count'],
                'monthly_breakdown': fees_summary['monthly_breakdown']
            },
            'expenses': {
                'total_expenses': total_expenses,
                'category_breakdown': expenses_summary['category_breakdown']
            },
            'net_balance': net_balance,
            'outstanding_fees': total_outstanding,
            'cash_position': net_balance  # Simplified cash position
        }

    @classmethod
    def get_term_financial_summary(cls, academic_year: str = None, term: str = None) -> Dict[str, Any]:
        """Get summary data strictly for a selected academic term."""
        academic_year = academic_year or config.Config.CURRENT_ACADEMIC_YEAR
        term = config.Config.normalize_term_name(term or config.Config.CURRENT_TERM)
        term_start, term_end = config.Config.get_term_date_bounds(term)
        fees_summary = FeePayment.get_total_collected_for_term(academic_year, term)
        academic_year_fees = FeePayment.get_total_collected_for_academic_year(academic_year)
        fee_totals = FeePayment.get_collected_by_fee_type_for_view(academic_year, term, term_start, term_end)
        expense_total = Expense.get_term_expense_total(academic_year, term)
        academic_year_expense_total = Expense.get_academic_year_expense_total(academic_year)
        expense_categories = Expense.get_term_category_breakdown(academic_year, term)
        expenses = Expense.get_term_expenses(academic_year, term, limit=50)
        monthly_map: Dict[str, Dict[str, float]] = {}
        for row in fees_summary.get('monthly_breakdown') or []:
            month = row.get('month')
            monthly_map[month] = {
                'income': float(row.get('total_amount') or 0),
                'expenses': 0.0,
                'payment_count': int(row.get('payment_count') or 0)
            }
        try:
            where_clause, params = Expense._term_scope_filter(academic_year, term)
            expense_rows = db.execute_query(
                f"""
                SELECT DATE_FORMAT(expense_date, '%Y-%m') AS month, COALESCE(SUM(amount), 0) AS total_expenses
                FROM expenses
                WHERE {where_clause}
                GROUP BY DATE_FORMAT(expense_date, '%Y-%m')
                ORDER BY month
                """,
                params,
                fetch=True
            ) or []
        except Exception:
            expense_rows = []
        for row in expense_rows:
            month = row.get('month')
            monthly_map.setdefault(month, {'income': 0.0, 'expenses': 0.0, 'payment_count': 0})
            monthly_map[month]['expenses'] = float(row.get('total_expenses') or 0)
        monthly_breakdown = []
        for month in sorted(k for k in monthly_map if k):
            income = float(monthly_map[month]['income'])
            expenses_value = float(monthly_map[month]['expenses'])
            monthly_breakdown.append({
                'month': month,
                'income': income,
                'expenses': expenses_value,
                'net': income - expenses_value,
                'payment_count': int(monthly_map[month].get('payment_count') or 0)
            })
        balances = cls.get_student_balances(academic_year, term=term)
        outstanding_total = sum(float(r.get('balance') or 0) for r in balances if float(r.get('balance') or 0) > 0)
        this_term_net = float(fees_summary.get('total_amount') or 0) - float(expense_total or 0)
        academic_year_net = float(academic_year_fees.get('total_amount') or 0) - float(academic_year_expense_total or 0)
        return {
            'academic_year': academic_year,
            'term': term,
            'term_start': term_start,
            'term_end': term_end,
            'total_income': float(fees_summary.get('total_amount') or 0),
            'total_expenses': float(expense_total or 0),
            'net_balance': this_term_net,
            'this_term': this_term_net,
            'year_to_date': this_term_net,
            'academic_year_total_income': float(academic_year_fees.get('total_amount') or 0),
            'academic_year_total_expenses': float(academic_year_expense_total or 0),
            'academic_year_net_balance': academic_year_net,
            'outstanding_fees': outstanding_total,
            'monthly_breakdown': monthly_breakdown,
            'expense_categories': expense_categories,
            'fee_totals': fee_totals,
            'recent_expenses': expenses
        }
    

    @staticmethod
    def get_collected_by_fee_type(start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """Return totals collected grouped by fee type for a period (wrapper for UI)."""
        try:
            if not start_date:
                start_date = date(date.today().year, 1, 1)
            if not end_date:
                end_date = date.today()

            query = """
                SELECT ft.fee_type_id, ft.fee_name, COALESCE(SUM(sf.amount_paid), 0) AS total_collected,
                       COUNT(sf.fee_id) AS payment_count
                FROM fee_types ft
                LEFT JOIN student_fees sf ON ft.fee_type_id = sf.fee_type_id AND sf.payment_date BETWEEN %s AND %s
                WHERE ft.academic_year = %s
                GROUP BY ft.fee_type_id, ft.fee_name
                ORDER BY total_collected DESC
            """
            results = db.execute_query(query, (start_date, end_date, config.Config.CURRENT_ACADEMIC_YEAR), fetch=True)
            return results
        except:
            return []
    
    @staticmethod
    def get_top_payers(limit: int = 10) -> List[Dict]:
        """Get top fee payers"""
        try:
            query = """
                SELECT 
                    s.student_id,
                    s.student_code,
                    CONCAT(s.first_name, ' ', s.last_name) as student_name,
                    s.class,
                    COALESCE(SUM(sf.amount_paid), 0) as total_paid,
                    COUNT(sf.fee_id) as payment_count
                FROM students s
                LEFT JOIN student_fees sf ON s.student_id = sf.student_id
                WHERE s.is_active = 1
                GROUP BY s.student_id, s.student_code, s.first_name, s.last_name, s.class
                ORDER BY total_paid DESC, s.student_id
                LIMIT %s
            """
            return db.execute_query(query, (limit,), fetch=True)
        except:
            return []
    
    @staticmethod
    def get_revenue_trend(days: int = 30) -> List[Dict]:
        """Get daily revenue trend for specified days"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            query = """
                SELECT 
                    payment_date as date,
                    SUM(amount_paid) as daily_revenue,
                    COUNT(*) as payment_count
                FROM student_fees
                WHERE payment_date BETWEEN %s AND %s
                GROUP BY payment_date
                ORDER BY payment_date
            """
            return db.execute_query(query, (start_date, end_date), fetch=True)
        except:
            return []

    @classmethod
    def start_new_term(cls, new_term: str, term_start_date: str = None):
        """Backward-compatible wrapper for centralized term rollover execution."""
        try:
            cls.execute_term_rollover(
                academic_year=config.Config.CURRENT_ACADEMIC_YEAR,
                from_term=config.Config.CURRENT_TERM,
                to_term=new_term,
                term_start_date=term_start_date
            )
            return True
        except Exception:
            return False

