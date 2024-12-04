# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

class TestPaymobCallbackLog(FrappeTestCase):
	def setUp(self):
		"""Set up a mock PaymobCallbackLog document for testing."""
		self.special_reference = "12345"

		# create team user
		self.team_user = frappe.get_doc({
			"doctype": "User",
			"email": "team_user@frappecloud.com",
			"first_name": "Test Team"
		}).insert(ignore_permissions=True, ignore_mandatory=True)

		self.team = frappe.get_doc({
			"doctype": "Team",
			"team_title": "Test Team",
			"user": self.team_user.name
		}).insert(ignore_permissions=True, ignore_mandatory=True)

		# Payment Partner User
		self.payment_partner_user = frappe.get_doc({
			"doctype": "User",
			"email": "payment_partner@frappecloud.com",
			"first_name": "Payment Partner Team"
		}).insert(ignore_permissions=True, ignore_mandatory=True)

		self.payment_partner = frappe.get_doc({
			"doctype": "Team",
			"team_title": "Test Payment Partner",
			"user": self.payment_partner_user.name
		}).insert(ignore_permissions=True, ignore_mandatory=True)

		# data needed to create Paymob Log
		tax_percentage = (14 / 100)
		exchange_rate = 48
		amount = 10
		amount_coverted_egp = (amount * exchange_rate)
		actual_amount = (amount_coverted_egp) + (amount_coverted_egp * tax_percentage)

		self.paymob_log = frappe.get_doc({
			"doctype": "Paymob Log",
			"special_reference": self.special_reference,
			"team": self.team.name,
			"payment_partner": self.payment_partner.name,
			"exchange_rate": exchange_rate,
			"amount": amount,
			"actual_amount": actual_amount
		}).insert(ignore_permissions=True)

		self.doc = frappe.get_doc({
			"doctype": "Paymob Callback Log",
			"event_type": "Transaction",
			"special_reference": self.special_reference,
			"payload": '{"obj": {"success": true, "is_live": true, "data": {"txn_response_code": "APPROVED"}}}',
			"team": None,
			"payment_partner": None,
			"submit_to_payment_partner": False
		}).insert(ignore_permissions=True)

	def tearDown(self):
		"""Clean up test records."""
		frappe.delete_doc("Team", self.team.name, ignore_permissions=True, force=True)
		frappe.delete_doc("Team", self.payment_partner.name, ignore_permissions=True, force=True)
		frappe.delete_doc("Paymob Log", self.paymob_log.name, ignore_permissions=True, force=True)
		frappe.delete_doc("Paymob Callback Log", self.doc.name, ignore_permissions=True, force=True)
		frappe.delete_doc("User", self.team_user.name, ignore_permissions=True, force=True)
		frappe.delete_doc("User", self.payment_partner_user.name, ignore_permissions=True, force=True)

	def test_set_missing_data(self):
		"""Test set_missing_data fetches and sets team and payment partner."""
		self.doc.set_missing_data()
		self.assertEqual(self.doc.team, self.team.name)
		self.assertEqual(self.doc.payment_partner, self.payment_partner.name)
		self.assertEqual(self.doc.special_reference, self.special_reference)


	def test_is_payment_successful(self):
		"""Test _is_payment_successful correctly parses payload and checks conditions."""
		# Valid success payload
		self.assertTrue(self.doc._is_payment_successful())

		# Payload with success = False
		self.doc.payload = '{"obj": {"success": false}}'
		self.assertFalse(self.doc._is_payment_successful())

		# Invalid payload format
		self.doc.payload = "invalid_json"
		self.assertFalse(self.doc._is_payment_successful())

		# Missing payload
		self.doc.payload = None
		self.assertFalse(self.doc._is_payment_successful())

	def test_create_payment_partner_transaction(self):
		"""Test _create_payment_partner_transaction creates transactions successfully."""
		self.doc.set_missing_data()
		self.doc._create_payment_partner_transaction()

		# Verify the transaction
		transaction = frappe.get_all("Payment Partner Transaction", filters={
			"team": self.doc.team,
			"payment_partner": self.doc.payment_partner,
			"amount": 10
		})

		self.assertTrue(len(transaction) > 0)
		transaction_doc = frappe.get_doc("Payment Partner Transaction", transaction[0].name)
		
		self.assertEqual(transaction_doc.amount, 10)
		self.assertEqual(transaction_doc.exchange_rate, 48)
		expected_actual_amount = 547.2
		self.assertEqual(transaction_doc.actual_amount, expected_actual_amount)
		self.assertEqual(transaction_doc.payment_partner, self.doc.payment_partner)

	def test_validate(self):
		"""Test validate triggers set_missing_data."""
		self.doc.team = None  # Reset team to trigger `set_missing_data`
		self.doc.validate()
		self.assertIsNotNone(self.doc.team)

	def test_after_insert(self):
		"""Test after_insert calls appropriate methods based on success."""
		# self.doc.team = None  # Reset team to trigger methods
		self.doc.after_insert()

		# Verify the transaction
		transaction = frappe.get_all("Payment Partner Transaction", filters={
			"team": self.doc.team,
			"payment_partner": self.doc.payment_partner
		})

		self.assertTrue(len(transaction) > 0)