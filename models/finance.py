"""
Compatibility facade for finance models.

The finance implementation is split into focused modules so this file can stay
small while existing imports such as `from models.finance import FeePayment`
continue to work.
"""
from .finance_fee_types import FeeType
from .finance_payments import FeePayment
from .finance_expenses import Expense
from .finance_balance import FinanceBalanceMixin
from .finance_rollover_setup import FinanceRolloverSetupMixin
from .finance_rollover_preview import FinanceRolloverPreviewMixin
from .finance_salary import FinanceSalaryMixin
from .finance_rollover_execute import FinanceRolloverExecuteMixin
from .finance_summary import FinanceSummaryMixin


class FinancialManager(
    FinanceBalanceMixin,
    FinanceRolloverSetupMixin,
    FinanceRolloverPreviewMixin,
    FinanceSalaryMixin,
    FinanceRolloverExecuteMixin,
    FinanceSummaryMixin,
):
    """Central finance service composed from focused finance modules.

    Mixin methods that call into other mixins are classmethods and resolve
    collaborators through ``cls``, so the composition order below is the
    single source of truth for method resolution.
    """


__all__ = ["FeeType", "FeePayment", "Expense", "FinancialManager"]
