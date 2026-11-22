"""Pure finance logic that does not need a database."""
import inspect
import unittest
from datetime import date

from tests import _support  # noqa: F401  (must be imported first)
from models import finance
from models.finance import FinancialManager as FM


class CompositionTestCase(unittest.TestCase):
    def test_facade_exports(self):
        for name in ("FeeType", "FeePayment", "Expense", "FinancialManager"):
            self.assertTrue(hasattr(finance, name), name)

    def test_mixins_do_not_depend_on_an_injected_global(self):
        # Mixins must resolve collaborators through `cls`, not a module-level
        # FinancialManager patched in after import.
        import models.finance_balance as m1
        import models.finance_rollover_execute as m2
        import models.finance_rollover_preview as m3
        import models.finance_rollover_setup as m4
        import models.finance_salary as m5
        import models.finance_summary as m6
        for module in (m1, m2, m3, m4, m5, m6):
            self.assertNotIn("FinancialManager", inspect.getsource(module), module.__name__)

    def test_cross_mixin_calls_resolve(self):
        for name in ("get_student_balances", "execute_term_rollover", "get_term_rollover_preview",
                     "start_new_term", "generate_monthly_salary_snapshot", "get_financial_summary"):
            self.assertTrue(callable(getattr(FM, name)), name)


class OpeningBalanceTestCase(unittest.TestCase):
    def test_no_carry_partial_payment(self):
        r = FM._allocate_opening_balance(10000, 4000, 0)
        self.assertEqual(r["balance"], 6000)
        self.assertEqual(r["opening_balance"], 10000)
        self.assertEqual(r["overpayment"], 0)

    def test_payment_settles_carried_balance_first(self):
        r = FM._allocate_opening_balance(10000, 3000, 5000)
        self.assertEqual(r["paid_to_carried_balance"], 3000)
        self.assertEqual(r["remaining_carried_balance"], 2000)
        self.assertEqual(r["paid_to_current_fees"], 0)
        self.assertEqual(r["balance"], 12000)

    def test_payment_spills_from_carry_into_current_fees(self):
        r = FM._allocate_opening_balance(10000, 8000, 5000)
        self.assertEqual(r["remaining_carried_balance"], 0)
        self.assertEqual(r["paid_to_current_fees"], 3000)
        self.assertEqual(r["balance"], 7000)

    def test_overpayment_reported(self):
        r = FM._allocate_opening_balance(10000, 12000, 0)
        self.assertEqual(r["overpayment"], 2000)
        self.assertEqual(r["effective_total_paid"], 10000)
        self.assertEqual(r["balance"], -2000)  # credit

    def test_explicit_split(self):
        r = FM._allocate_opening_balance(10000, None, 5000, carried_paid=2000, current_paid=4000)
        self.assertEqual(r["remaining_carried_balance"], 3000)
        self.assertEqual(r["current_term_balance"], 6000)
        self.assertEqual(r["balance"], 9000)


class HelpersTestCase(unittest.TestCase):
    def test_next_term_cycles(self):
        self.assertEqual(FM._get_next_term_name("Term 1"), "Term 2")
        self.assertEqual(FM._get_next_term_name("Term 3"), "Term 1")
        self.assertEqual(FM._get_next_term_name("unknown"), "Term 1")

    def test_month_bounds(self):
        self.assertEqual(FM._month_bounds("2026-02"), (date(2026, 2, 1), date(2026, 3, 1)))
        self.assertEqual(FM._month_bounds("2026-12"), (date(2026, 12, 1), date(2027, 1, 1)))

    def test_excluded_ids_are_sanitised(self):
        self.assertEqual(FM._normalize_excluded_carry_student_ids(["3", 4, None, "x", -1, 0]), {3, 4})

    def test_fee_signature_ignores_case_and_class_order(self):
        a = {"fee_name": " Tuition ", "is_required": 1, "class_names": ["Std 2", "Std 1"]}
        b = {"fee_name": "tuition", "is_required": True, "class_names": ["Std 1", "Std 2"]}
        self.assertEqual(FM._fee_template_signature(a), FM._fee_template_signature(b))

    def test_parse_term_schedule_date(self):
        self.assertEqual(FM._parse_term_schedule_date("2026-01-05"), date(2026, 1, 5))
        self.assertIsNone(FM._parse_term_schedule_date("not a date"))
        self.assertIsNone(FM._parse_term_schedule_date(None))


class ExpenseValidationTestCase(unittest.TestCase):
    def test_zero_amount_rejected(self):
        ok, _ = finance.Expense(description="Chalk", amount=0).validate()
        self.assertFalse(ok)

    def test_future_date_rejected(self):
        ok, _ = finance.Expense(description="Chalk", amount=10, expense_date=date(2999, 1, 1)).validate()
        self.assertFalse(ok)

    def test_valid_expense(self):
        ok, msg = finance.Expense(description="Chalk", amount=10).validate()
        self.assertTrue(ok, msg)


if __name__ == "__main__":
    unittest.main()
