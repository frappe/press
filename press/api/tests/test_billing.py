import frappe

from unittest import TestCase
from press.api.billing import (
	get_cleaned_up_transactions,
	get_processed_balance_transactions,
)
from frappe.core.utils import find

test_bts = [
	{
		"name": "BT-2022-00065",
		"type": "Applied To Invoice",
		"source": "",
		"amount": -200.0,
		"ending_balance": 200.0,
		"invoice": "INV-2022-00122",
		"description": None,
	},
	{
		"name": "BT-2022-00064",
		"type": "Applied To Invoice",
		"source": "",
		"amount": -500.0,
		"ending_balance": 400.0,
		"invoice": "INV-2022-00121",
		"description": None,
	},
	{
		"name": "BT-2022-00063",
		"type": "Adjustment",
		"source": "Free Credits",
		"amount": 200.0,
		"ending_balance": 900.0,
		"invoice": None,
		"description": "Reverse amount ₹ 200.00 of BT-2022-00059 from invoice INV-2022-00121",
	},
	{
		"name": "BT-2022-00062",
		"type": "Adjustment",
		"source": "Prepaid Credits",
		"amount": 200.0,
		"ending_balance": 700.0,
		"invoice": None,
		"description": "Reverse amount ₹ 200.00 of BT-2022-00058 from invoice INV-2022-00121",
	},
	{
		"name": "BT-2022-00061",
		"type": "Adjustment",
		"source": "Prepaid Credits",
		"amount": 500.0,
		"ending_balance": 500.0,
		"invoice": None,
		"description": None,
	},
	{
		"name": "BT-2022-00060",
		"type": "Applied To Invoice",
		"source": "",
		"amount": -400.0,
		"ending_balance": 0.0,
		"invoice": "INV-2022-00121",
		"description": None,
	},
	{
		"name": "BT-2022-00059",
		"type": "Adjustment",
		"source": "Free Credits",
		"amount": 200.0,
		"ending_balance": 400.0,
		"invoice": None,
		"description": "Reverse amount ₹ 200.00 of BT-2022-00056 from invoice INV-2022-00121",
	},
	{
		"name": "BT-2022-00058",
		"type": "Adjustment",
		"source": "Prepaid Credits",
		"amount": 200.0,
		"ending_balance": 200.0,
		"invoice": None,
		"description": "Reverse amount ₹ 200.00 of BT-2022-00055 from invoice INV-2022-00121",
	},
	{
		"name": "BT-2022-00057",
		"type": "Applied To Invoice",
		"source": "",
		"amount": -400.0,
		"ending_balance": 0.0,
		"invoice": "INV-2022-00121",
		"description": None,
	},
	{
		"name": "BT-2022-00056",
		"type": "Adjustment",
		"source": "Free Credits",
		"amount": 200.0,
		"ending_balance": 400.0,
		"invoice": None,
		"description": "Reverse amount ₹ 200.00 of BT-2022-00052 from invoice INV-2022-00121",
	},
	{
		"name": "BT-2022-00055",
		"type": "Adjustment",
		"source": "Prepaid Credits",
		"amount": 200.0,
		"ending_balance": 200.0,
		"invoice": None,
		"description": "Reverse amount ₹ 200.00 of BT-2022-00051 from invoice INV-2022-00121",
	},
	{
		"name": "BT-2022-00054",
		"type": "Applied To Invoice",
		"source": "",
		"amount": -400.0,
		"ending_balance": 0.0,
		"invoice": "INV-2022-00121",
		"description": None,
	},
	{
		"name": "BT-2022-00053",
		"type": "Applied To Invoice",
		"source": "",
		"amount": -300.0,
		"ending_balance": 400.0,
		"invoice": "INV-2022-00120",
		"description": None,
	},
	{
		"name": "BT-2022-00052",
		"type": "Adjustment",
		"source": "Free Credits",
		"amount": 200.0,
		"ending_balance": 700.0,
		"invoice": None,
		"description": "Reverse amount ₹ 200.00 of BT-2022-00049 from invoice INV-2022-00120",
	},
	{
		"name": "BT-2022-00051",
		"type": "Adjustment",
		"source": "Prepaid Credits",
		"amount": 500.0,
		"ending_balance": 500.0,
		"invoice": None,
		"description": None,
	},
	{
		"name": "BT-2022-00050",
		"type": "Applied To Invoice",
		"source": "",
		"amount": -200.0,
		"ending_balance": 0.0,
		"invoice": "INV-2022-00120",
		"description": None,
	},
	{
		"name": "BT-2022-00049",
		"type": "Adjustment",
		"source": "Free Credits",
		"amount": 200.0,
		"ending_balance": 200.0,
		"invoice": None,
		"description": None,
	},
]


class TestBalances(TestCase):
	def test_clean_up_balances(self):
		clean_transactions = get_cleaned_up_transactions([frappe._dict(d) for d in test_bts])

		self.assertEqual(len(clean_transactions), 6)

		# Reversal transactions, must not be present
		self.assertFalse(find(clean_transactions, lambda x: x.name == "BT-2022-00063"))
		self.assertFalse(find(clean_transactions, lambda x: x.name == "BT-2022-00059"))
		self.assertFalse(find(clean_transactions, lambda x: x.name == "BT-2022-00058"))

		# Applied to invoices, but have been reversed, hence must not be present
		self.assertFalse(find(clean_transactions, lambda x: x.name == "BT-2022-00050"))
		self.assertFalse(find(clean_transactions, lambda x: x.name == "BT-2022-00060"))

		# Applied to invoice, not reversed, hence must be present
		self.assertTrue(find(clean_transactions, lambda x: x.name == "BT-2022-00053"))
		self.assertTrue(find(clean_transactions, lambda x: x.name == "BT-2022-00061"))
		self.assertTrue(find(clean_transactions, lambda x: x.name == "BT-2022-00065"))

		# Added credits, must be present
		self.assertTrue(find(clean_transactions, lambda x: x.name == "BT-2022-00049"))
		self.assertTrue(find(clean_transactions, lambda x: x.name == "BT-2022-00051"))
