"""Inventory usage rules (database calls are faked)."""
import unittest
from unittest import mock

from tests import _support  # noqa: F401  (must be imported first)
from models.inventory import InventoryItem, InventoryManager


class UseItemTestCase(unittest.TestCase):
    def _item(self, qty):
        return InventoryItem(item_id=1, item_name="Chalk", category="Stationery", quantity=qty,
                             unit_price=100, min_quantity=1, max_quantity=100)

    def test_rejects_non_positive_quantity(self):
        with mock.patch.object(InventoryItem, "get_by_id", return_value=self._item(10)):
            ok, _ = InventoryManager.use_item(1, 0)
        self.assertFalse(ok)

    def test_rejects_more_than_available(self):
        with mock.patch.object(InventoryItem, "get_by_id", return_value=self._item(2)):
            ok, msg = InventoryManager.use_item(1, 5)
        self.assertFalse(ok)
        self.assertIn("Insufficient", msg)

    def test_consumes_stock_without_recording_an_expense(self):
        item = self._item(10)
        with mock.patch.object(InventoryItem, "get_by_id", return_value=item), \
             mock.patch.object(InventoryItem, "update_quantity", return_value=(True, "ok")) as upd, \
             mock.patch("models.finance_expenses.Expense.save") as expense_save:
            ok, _ = InventoryManager.use_item(1, 3, "class use")
        self.assertTrue(ok)
        upd.assert_called_once_with(-3)
        expense_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
