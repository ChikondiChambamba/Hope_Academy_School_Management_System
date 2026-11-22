"""Term rollover rules: academic-year progression, carried debt and carried credit."""
import random
import unittest
from unittest import mock

from tests import _support  # noqa: F401  (must be imported first)
import config
from models.finance import FinancialManager as FM

C = config.Config
CARRY_FEE = "Carried Forward Fee Balance"


class AcademicPeriodTestCase(unittest.TestCase):
    def test_next_academic_year_formats(self):
        self.assertEqual(C.next_academic_year("2025-2026"), "2026-2027")
        self.assertEqual(C.next_academic_year("2025/26"), "2026/27")
        self.assertEqual(C.next_academic_year("2099/99"), "2100/00")
        self.assertEqual(C.next_academic_year("2025"), "2026")
        with self.assertRaises(ValueError):
            C.next_academic_year("next year")

    def test_terms_advance_within_year_then_year_moves_forward(self):
        self.assertEqual(C.next_term_period("2025-2026", "Term 1"), ("2025-2026", "Term 2"))
        self.assertEqual(C.next_term_period("2025-2026", "Term 2"), ("2025-2026", "Term 3"))
        self.assertEqual(C.next_term_period("2025-2026", "Term 3"), ("2026-2027", "Term 1"))

    def test_rollover_target_defaults_to_next_period(self):
        self.assertEqual(FM._resolve_rollover_target("2025-2026", "Term 3"), ("2026-2027", "Term 1"))
        self.assertEqual(FM._resolve_rollover_target("2025-2026", "Term 3", "Term 1"), ("2026-2027", "Term 1"))

    def test_rollover_cannot_skip_a_term(self):
        with self.assertRaises(ValueError):
            FM._resolve_rollover_target("2025-2026", "Term 1", "Term 3")

    def test_year_end_rollover_cannot_stay_in_old_year(self):
        with self.assertRaises(ValueError):
            FM._resolve_rollover_target("2025-2026", "Term 3", "Term 1", "2025-2026")

    def test_stale_dates_are_cleared(self):
        schedule = {
            "Term 1": {"start_date": "2025-09-01", "end_date": "2025-12-15"},
            "Term 2": {"start_date": "2026-01-05", "end_date": "2026-04-10"},
            "Term 3": {"start_date": "2026-04-27", "end_date": "2026-07-31"},
        }
        cleaned = C.clear_stale_term_dates(
            {**schedule, "Term 1": {"start_date": "2026-09-07", "end_date": None}},
            C.parse_config_date("2026-07-31"),
        )
        self.assertEqual(cleaned["Term 1"], {"start_date": "2026-09-07", "end_date": None})
        self.assertEqual(cleaned["Term 2"], {"start_date": None, "end_date": None})
        self.assertEqual(cleaned["Term 3"], {"start_date": None, "end_date": None})


class AllocationTestCase(unittest.TestCase):
    def test_excess_paid_against_carry_is_not_lost(self):
        # Paid 7,000 against a 5,000 carried balance: 2,000 reduces current fees.
        r = FM._allocate_opening_balance(10000, None, 5000, carried_paid=7000, current_paid=0)
        self.assertEqual(r["remaining_carried_balance"], 0)
        self.assertEqual(r["paid_to_current_fees"], 2000)
        self.assertEqual(r["balance"], 8000)

    def test_credit_brought_forward_reduces_fees(self):
        r = FM._allocate_opening_balance(10000, 3000, -2000)
        self.assertEqual(r["credit_brought_forward"], 2000)
        self.assertEqual(r["remaining_carried_balance"], 0)
        self.assertEqual(r["balance"], 5000)

    def test_overpayment_becomes_credit(self):
        r = FM._allocate_opening_balance(10000, None, 5000, carried_paid=6000, current_paid=11000)
        self.assertEqual(r["balance"], -2000)
        self.assertEqual(r["overpayment"], 2000)

    def test_no_money_is_ever_dropped(self):
        rng = random.Random(7)
        for _ in range(500):
            fees = rng.choice([0, rng.randint(0, 200000)])
            carried = rng.randint(-50000, 80000)
            carried_paid = rng.randint(0, 100000)
            current_paid = rng.randint(0, 250000)
            r = FM._allocate_opening_balance(fees, None, carried, carried_paid, current_paid)
            self.assertAlmostEqual(r["balance"], carried + fees - carried_paid - current_paid)
            self.assertGreaterEqual(r["remaining_carried_balance"], 0)
            self.assertAlmostEqual(r["overpayment"], max(-r["balance"], 0))


def fee_row(sid, fee, expected, paid, required=1, specific=0, fee_type_id=None):
    return {"student_id": sid, "student_code": f"S{sid}", "student_name": f"Student {sid}",
            "class_name": "Std 1", "fee_type_id": fee_type_id, "fee_name": fee,
            "is_required": required, "is_class_specific": specific,
            "expected_amount": expected, "paid_amount": paid}


def carry_row(sid, fee, amount, required=1):
    return {"student_id": sid, "student_code": f"S{sid}", "student_name": f"Student {sid}",
            "class_name": "Std 1", "source_fee_name": fee, "source_is_required": required,
            "source_is_class_specific": 0, "carried_amount": amount, "source_status": "Carried Forward"}


class PreviewTestCase(unittest.TestCase):
    def build(self, source, prior=(), next_rows=None, excluded=None,
              years=("2025-2026", "Term 3", "2026-2027", "Term 1")):
        next_rows = next_rows if next_rows is not None else [fee_row(s["student_id"], "Tuition", 85000, 0)
                                                             for s in source]
        calls = []

        def fee_rows(year, term, treat_new_students_as_continuing=False, promote_classes=False):
            calls.append((year, term))
            return list(source) if (year, term) == years[:2] else list(next_rows)

        with mock.patch.object(FM, "_student_fee_rows_for_term", side_effect=fee_rows), \
             mock.patch.object(FM, "_existing_carried_rows_for_term", return_value=list(prior)) as prior_mock, \
             mock.patch.object(FM, "_build_projected_term_fee_rows", return_value=([], 0)) as proj:
            preview = FM._build_term_rollover_preview(*years, excluded_student_ids=excluded)
        return preview, calls, prior_mock, proj

    def row(self, preview, sid=1):
        return next(r for r in preview["rows"] if r["student_id"] == sid)

    def test_year_end_reads_old_year_and_targets_new_year(self):
        preview, calls, prior_mock, proj = self.build([fee_row(1, "Tuition", 85000, 85000)])
        self.assertIn(("2025-2026", "Term 3"), calls)
        self.assertIn(("2026-2027", "Term 1"), calls)
        prior_mock.assert_called_once_with("2025-2026", "Term 3")
        proj.assert_called_once_with("2025-2026", "Term 3", "2026-2027", "Term 1",
                                     treat_new_students_as_continuing=True, promote_classes=True)
        self.assertEqual(preview["to_academic_year"], "2026-2027")

    def test_unpaid_required_fee_is_carried(self):
        preview, *_ = self.build([fee_row(1, "Tuition", 85000, 60000)])
        self.assertEqual(self.row(preview)["carry_forward_total"], 25000)
        self.assertEqual(self.row(preview)["opening_balance"], 85000 + 25000)

    def test_prior_carry_paid_during_term_is_not_carried_again(self):
        source = [fee_row(1, "Tuition", 85000, 85000), fee_row(1, CARRY_FEE, 0, 20000)]
        preview, *_ = self.build(source, prior=[carry_row(1, "Tuition", 20000)])
        self.assertEqual(self.row(preview)["carry_forward_total"], 0)

    def test_partly_paid_prior_carry_carries_the_rest(self):
        source = [fee_row(1, "Tuition", 85000, 85000), fee_row(1, CARRY_FEE, 0, 5000)]
        preview, *_ = self.build(source, prior=[carry_row(1, "Tuition", 20000)])
        self.assertEqual(self.row(preview)["carry_forward_total"], 15000)

    def test_overpayment_is_carried_as_credit(self):
        preview, *_ = self.build([fee_row(1, "Tuition", 85000, 95000)])
        row = self.row(preview)
        self.assertEqual(row["carry_forward_total"], -10000)
        self.assertEqual(row["carry_status"], "Credit")
        self.assertEqual(row["opening_balance"], 85000 - 10000)
        self.assertEqual(preview["summary"]["credit_students"], 1)
        self.assertEqual(preview["summary"]["credit_carried_total"], 10000)

    def test_overpaying_the_carried_balance_is_credit(self):
        source = [fee_row(1, "Tuition", 85000, 85000), fee_row(1, CARRY_FEE, 0, 26000)]
        preview, *_ = self.build(source, prior=[carry_row(1, "Tuition", 20000)])
        self.assertEqual(self.row(preview)["carry_forward_total"], -6000)

    def test_credit_settles_other_debt_first(self):
        source = [fee_row(1, "Tuition", 85000, 95000), fee_row(1, "Exam", 15000, 0)]
        preview, *_ = self.build(source)
        self.assertEqual(self.row(preview)["carry_forward_total"], 5000)

    def test_credit_settles_fee_that_would_be_reset(self):
        # Optional fee not offered next term would be written off, but the
        # student's overpayment covers it first; only the remainder is credit.
        source = [fee_row(1, "Tuition", 85000, 95000), fee_row(1, "Trip", 4000, 0, required=0)]
        preview, *_ = self.build(source)
        row = self.row(preview)
        self.assertEqual(row["carry_forward_total"], -6000)
        self.assertEqual(row["reset_amount"], 0)

    def test_credit_brought_in_and_unused_is_carried_on(self):
        preview, *_ = self.build([fee_row(1, "Tuition", 85000, 85000)], prior=[carry_row(1, "Credit Balance", -3000)])
        self.assertEqual(self.row(preview)["carry_forward_total"], -3000)

    def test_excluded_student_has_debt_reset_but_keeps_credit(self):
        source = [fee_row(1, "Tuition", 85000, 60000), fee_row(2, "Tuition", 85000, 90000)]
        preview, *_ = self.build(source, excluded=[1, 2])
        self.assertEqual(self.row(preview, 1)["carry_forward_total"], 0)
        self.assertEqual(self.row(preview, 1)["reset_amount"], 25000)
        self.assertEqual(self.row(preview, 2)["carry_forward_total"], -5000)

    def test_net_carry_equals_owed_minus_paid_minus_written_off(self):
        source = [fee_row(1, "Tuition", 85000, 70000), fee_row(1, "Exam", 15000, 18000),
                  fee_row(1, CARRY_FEE, 0, 4000), fee_row(1, "Trip", 4000, 0, required=0)]
        preview, *_ = self.build(source, prior=[carry_row(1, "Tuition", 10000)])
        row = self.row(preview)
        owed = 85000 + 15000 + 4000 + 10000
        paid = 70000 + 18000 + 4000
        self.assertAlmostEqual(row["carry_forward_total"], owed - paid - row["reset_amount"])


class ExecutionHelpersTestCase(unittest.TestCase):
    def test_same_named_lines_merge_into_one_row(self):
        merged = FM._merge_carry_details([
            {"fee_name": "Tuition", "carried_amount": 20000, "expected_amount": 20000, "paid_amount": 0},
            {"fee_name": "tuition ", "carried_amount": 25000, "expected_amount": 85000, "paid_amount": 60000,
             "fee_type_id": 9},
            {"fee_name": "Exam", "carried_amount": 0},
            {"fee_name": "Credit Balance", "carried_amount": -3000},
        ])
        by_name = {d["fee_name"].strip().lower(): d for d in merged}
        self.assertEqual(set(by_name), {"tuition", "credit balance"})
        self.assertEqual(by_name["tuition"]["carried_amount"], 45000)
        self.assertEqual(by_name["tuition"]["fee_type_id"], 9)
        self.assertEqual(by_name["credit balance"]["carried_amount"], -3000)

    def test_year_end_advances_config_and_clears_old_dates(self):
        saved = {k: getattr(C, k) for k in ("CURRENT_ACADEMIC_YEAR", "CURRENT_TERM", "PREVIOUS_ACADEMIC_YEAR",
                                            "PREVIOUS_TERM", "TERM_SCHEDULE", "ACADEMIC_YEAR_START_DATE",
                                            "ACADEMIC_YEAR_END_DATE", "TERM_START_DATE", "TERM_END_DATE")}
        try:
            C.TERM_SCHEDULE = {"Term 1": {"start_date": "2025-09-01", "end_date": "2025-12-15"},
                               "Term 2": {"start_date": "2026-01-05", "end_date": "2026-04-10"},
                               "Term 3": {"start_date": "2026-04-27", "end_date": "2026-07-31"}}
            C.ACADEMIC_YEAR_START_DATE, C.ACADEMIC_YEAR_END_DATE = "2025-09-01", "2026-07-31"
            FM._advance_configured_period("2025-2026", "Term 3", "2026-2027", "Term 1", "2026-09-07")
            self.assertEqual((C.CURRENT_ACADEMIC_YEAR, C.CURRENT_TERM), ("2026-2027", "Term 1"))
            self.assertEqual((C.PREVIOUS_ACADEMIC_YEAR, C.PREVIOUS_TERM), ("2025-2026", "Term 3"))
            self.assertEqual(C.TERM_SCHEDULE["Term 1"]["start_date"], "2026-09-07")
            self.assertIsNone(C.TERM_SCHEDULE["Term 2"]["start_date"])
            self.assertIsNone(C.ACADEMIC_YEAR_END_DATE)
        finally:
            for k, v in saved.items():
                setattr(C, k, v)

    def test_new_term_cannot_start_before_closing_term_ends(self):
        saved = C.TERM_SCHEDULE
        try:
            C.TERM_SCHEDULE = {"Term 3": {"start_date": "2026-04-27", "end_date": "2026-07-31"}}
            with mock.patch.object(FM, "_build_term_rollover_preview") as build:
                with self.assertRaises(ValueError):
                    FM.execute_term_rollover("2025-2026", "Term 3", term_start_date="2026-05-01")
                build.assert_not_called()
        finally:
            C.TERM_SCHEDULE = saved


if __name__ == "__main__":
    unittest.main()
