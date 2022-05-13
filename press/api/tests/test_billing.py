import frappe

from unittest import TestCase
from press.api.billing import get_cleaned_up_transactions, get_processed_balance_transactions

class TestBalances(TestCase):
    def test_clean_up_balances(self):
        pass