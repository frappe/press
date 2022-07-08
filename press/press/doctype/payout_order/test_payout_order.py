# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import frappe

from frappe.tests.utils import FrappeTestCase
from press.press.doctype.payout_order.payout_order import (
	create_payout_order_from_invoice_items,
)


class TestPayoutOrder(FrappeTestCase):
	def test_net_amount_calculations_inr(self):
		self.create_test_inr_invoice()
		po = create_payout_order_from_invoice_items(
			self.test_invoice.items, self.test_team.name, mode_of_payment="Internal", save=True
		)

		self.assertEqual(len(po.items), 1)
		self.assertEqual(po.items[0].invoice, self.test_invoice.name)
		self.assertEqual(po.items[0].total_amount, 40.0)
		self.assertEqual(po.items[0].gateway_fee, (200 / 1000) * 40)
		self.assertEqual(po.items[0].net_amount, 32.0)
		self.assertEqual(po.items[0].currency, "INR")

		self.assertEqual(po.net_total_inr, 32.0)
		self.assertEqual(po.net_total_usd, 0)

	def test_net_amount_calculations_usd(self):
		self.create_test_usd_invoice()

		po = create_payout_order_from_invoice_items(
			self.test_invoice.items, self.test_team.name, mode_of_payment="Internal", save=True
		)

		self.assertEqual(len(po.items), 1)
		self.assertEqual(po.items[0].invoice, self.test_invoice.name)
		self.assertEqual(po.items[0].total_amount, 20.0)

		expected_gateway_fee = 14.4
		self.assertEqual(po.items[0].gateway_fee, expected_gateway_fee)
		self.assertEqual(po.items[0].net_amount, 20.0 - expected_gateway_fee)
		self.assertEqual(po.items[0].currency, "USD")

		self.assertEqual(po.net_total_inr, 0)
		self.assertEqual(po.net_total_usd, 20.0 - expected_gateway_fee)

	def create_test_inr_invoice(self):
		self.test_team = frappe.get_doc(
			doctype="Team", name="testuserinr@example.com", country="India", enabled=1
		).insert()

		self.test_invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.test_team.name,
			transaction_amount=1000,
			transaction_fee=200,
			amount_paid=1000,
			status="Paid",
		).insert()

		self.test_usage_record = frappe.get_doc(
			doctype="Usage Record", team=self.test_team.name, amount=500
		).insert()

		self.test_invoice.append(
			"items",
			{
				"document_type": "Usage Record",
				"document_name": self.test_usage_record.name,
				"rate": 20,
				"plan": "INR 100",
				"quantity": 2,
			},
		)

		self.test_invoice.save()
		self.test_invoice.submit()

	def create_test_usd_invoice(self):
		self.test_team = frappe.get_doc(
			doctype="Team", name="testuserusd@example.com", country="United States", enabled=1
		).insert()

		self.test_invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.test_team.name,
			transaction_amount=1800,
			transaction_fee=1260,
			amount_paid=25,
			status="Paid",
			exchange_rate=70,
		).insert()

		self.test_usage_record = frappe.get_doc(
			doctype="Usage Record", team=self.test_team.name, amount=15
		).insert()

		self.test_invoice.append(
			"items",
			{
				"document_type": "Usage Record",
				"document_name": self.test_usage_record.name,
				"rate": 10,
				"plan": "USD 25",
				"quantity": 2,
			},
		)

		self.test_invoice.save()
		self.test_invoice.submit()

	def tearDown(self):
		frappe.db.rollback()
