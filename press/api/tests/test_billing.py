from unittest import TestCase
from unittest.mock import MagicMock, patch

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase

from press.api.billing import (
	get_cleaned_up_transactions,
	get_processed_balance_transactions,
	verify_m_pesa_transaction,
)
from press.press.doctype.team.test_team import create_test_team
from press.utils.mpesa_utils import create_mpesa_request_log

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

	def test_processed_balances(self):
		processed_transactions = get_processed_balance_transactions([frappe._dict(d) for d in test_bts])

		self.assertEqual(len(processed_transactions), 6)

		# Testing the order of transactions
		self.assertEqual(processed_transactions[0].name, "BT-2022-00065")
		self.assertEqual(processed_transactions[-1].name, "BT-2022-00049")

		# Testing first and last ending balances
		self.assertEqual(processed_transactions[0].ending_balance, 200)
		self.assertEqual(processed_transactions[-1].ending_balance, 200)

		# Testing ending balance calculation
		self.assertEqual(processed_transactions[-1].ending_balance, 200)
		self.assertEqual(processed_transactions[-2].ending_balance, 700)  # Added 500 in credits
		self.assertEqual(processed_transactions[-3].ending_balance, 400)  # Applied to invoice, -300
		self.assertEqual(processed_transactions[-4].ending_balance, 900)  # Added 500 in credits
		self.assertEqual(processed_transactions[-5].ending_balance, 400)  # Applied to invoice, -500
		self.assertEqual(processed_transactions[-6].ending_balance, 200)  # Applied to invoice, -200


class TestVerifyMpesaTransaction(FrappeTestCase):
	"""The STK callback is unauthenticated, so credit must depend on Mpesa's own answer."""

	CHECKOUT_ID = "ws_CO_test_checkout_request"

	def setUp(self):
		super().setUp()

		self.team = create_test_team()
		self.partner = create_test_team()
		self.partner.db_set("erpnext_partner", 1)

		frappe.get_doc(
			{
				"doctype": "Mpesa Setup",
				"team": self.partner.name,
				"mpesa_setup_id": "test-mpesa-setup",
				"api_type": "Mpesa Express",
				"consumer_key": "test_consumer_key",
				"consumer_secret": "test_consumer_secret",
				"business_shortcode": "174379",
				"till_number": "174379",
				"pass_key": "test_pass_key",
				"security_credential": "test_security_credential",
				"sandbox": 1,
			}
		).insert(ignore_permissions=True)

		create_mpesa_request_log(
			{
				"team": self.team.name,
				"partner": self.partner.user,
				"request_amount": 6500,
				"amount_usd": 50,
				"exchange_rate": 130,
			},
			"Host",
			"Mpesa Express",
			self.CHECKOUT_ID,
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def success_callback(self):
		return {
			"Body": {
				"stkCallback": {
					"MerchantRequestID": "test-merchant-request",
					"CheckoutRequestID": self.CHECKOUT_ID,
					"ResultCode": 0,
					"ResultDesc": "The service request is processed successfully.",
					"CallbackMetadata": {
						"Item": [
							{"Name": "Amount", "Value": 6500},
							{"Name": "MpesaReceiptNumber", "Value": "TEST1RECEIPT"},
							{"Name": "TransactionDate", "Value": 20250101120000},
							{"Name": "PhoneNumber", "Value": 254700000000},
						]
					},
				}
			}
		}

	def connector_answering(self, result_code):
		connector = MagicMock()
		connector.stk_push_query.return_value = {
			"ResultCode": result_code,
			"ResultDesc": "Test query response",
			"CheckoutRequestID": self.CHECKOUT_ID,
		}
		return MagicMock(return_value=connector)

	def test_callback_is_rejected_when_mpesa_says_the_customer_did_not_pay(self):
		with patch(
			"press.api.regional_payments.mpesa.utils.MpesaConnector",
			new=self.connector_answering("1032"),
		):
			response = verify_m_pesa_transaction(**self.success_callback())

		self.assertEqual(response["status"], "Failed")
		self.assertFalse(frappe.db.exists("Mpesa Payment Record", {"transaction_id": self.CHECKOUT_ID}))
		self.assertFalse(frappe.db.exists("Balance Transaction", {"team": self.team.name}))

	def test_rejected_callback_leaves_a_failed_request_log_behind(self):
		with patch(
			"press.api.regional_payments.mpesa.utils.MpesaConnector",
			new=self.connector_answering("1032"),
		):
			verify_m_pesa_transaction(**self.success_callback())

		self.assertTrue(
			frappe.db.exists("Mpesa Request Log", {"request_id": self.CHECKOUT_ID, "status": "Failed"})
		)

	def test_callback_is_accepted_when_mpesa_confirms_the_payment(self):
		with (
			patch(
				"press.api.regional_payments.mpesa.utils.MpesaConnector",
				new=self.connector_answering("0"),
			),
			patch("press.api.billing.create_mpesa_payment_record") as create_payment_record,
		):
			response = verify_m_pesa_transaction(**self.success_callback())

		self.assertEqual(response["status"], "Completed")
		create_payment_record.assert_called_once()
