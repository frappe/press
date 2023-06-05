# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import frappe

from frappe.tests.utils import FrappeTestCase
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.marketplace_app.test_marketplace_app import (
	create_test_marketplace_app,
)
from press.press.doctype.payout_order.payout_order import (
	create_marketplace_payout_orders_monthly,
	create_payout_order_from_invoice_items,
)
from press.press.doctype.team.test_team import create_test_team


class TestPayoutOrder(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_net_amount_calculations_inr(self):
		self.create_test_inr_invoice()
		# Create a PO for this period
		today = frappe.utils.today()
		period_start = frappe.utils.data.get_first_day(today)
		period_end = frappe.utils.data.get_last_day(today)

		po = create_payout_order_from_invoice_items(
			self.test_invoice.items,
			self.test_team.name,
			period_start=period_start,
			period_end=period_end,
			mode_of_payment="Internal",
			save=True,
		)

		self.assertEqual(len(po.items), 1)
		self.assertEqual(po.items[0].invoice, self.test_invoice.name)
		self.assertEqual(po.items[0].total_amount, 40.0)
		self.assertEqual(po.items[0].net_amount, 40.0)
		self.assertEqual(po.items[0].currency, "INR")

		self.assertEqual(po.net_total_inr, 40.0)
		self.assertEqual(po.net_total_usd, 0)

	def test_net_amount_calculations_usd(self):
		self.create_test_usd_invoice()

		# Create a PO for this period
		today = frappe.utils.today()
		period_start = frappe.utils.data.get_first_day(today)
		period_end = frappe.utils.data.get_last_day(today)

		po = create_payout_order_from_invoice_items(
			self.test_invoice.items,
			self.test_team.name,
			period_start=period_start,
			period_end=period_end,
			mode_of_payment="Internal",
			save=True,
		)

		self.assertEqual(len(po.items), 1)
		self.assertEqual(po.items[0].invoice, self.test_invoice.name)
		self.assertEqual(po.items[0].total_amount, 20.0)

		self.assertEqual(po.items[0].net_amount, 20.0)
		self.assertEqual(po.items[0].currency, "USD")

		self.assertEqual(po.net_total_inr, 0)
		self.assertEqual(po.net_total_usd, 20.0)

	def create_test_inr_invoice(self):
		self.test_team = create_test_team()

		self.test_invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.test_team.name,
			transaction_amount=1000,
			transaction_fee=200,
			amount_paid=1000,
			status="Paid",
		).insert()

		# create test marketplace app
		test_app = create_test_app("test_app")
		test_mp_app = create_test_marketplace_app(test_app.name, self.test_team.name)

		self.test_invoice.append(
			"items",
			{
				"document_type": "Marketplace App",
				"document_name": test_mp_app.name,
				"rate": 20,
				"plan": "INR 100",
				"quantity": 2,
			},
		)

		self.test_invoice.save()
		self.test_invoice.submit()

	def create_test_usd_invoice(self):
		self.test_team = create_test_team(country="United States")

		self.test_invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.test_team.name,
			transaction_amount=1800,
			transaction_fee=1260,
			amount_paid=25,
			status="Paid",
			exchange_rate=70,
		).insert()

		# create test marketplace app
		test_app = create_test_app("test_app")
		test_mp_app = create_test_marketplace_app(test_app.name, self.test_team.name)

		self.test_invoice.append(
			"items",
			{
				"document_type": "Marketplace App",
				"document_name": test_mp_app.name,
				"rate": 10,
				"plan": "USD 25",
				"quantity": 2,
			},
		)

		self.test_invoice.save()
		self.test_invoice.submit()

	def test_create_marketplace_monthly_payout_order(self):
		self.create_test_usd_invoice()

		# No payout order before running the job
		self.assertFalse(frappe.db.exists("Payout Order", {"recipient": self.test_team.name}))

		# Run the monthly job
		create_marketplace_payout_orders_monthly()

		# The Payout Order should have been created
		self.assertTrue(frappe.db.exists("Payout Order", {"recipient": self.test_team.name}))

		po = frappe.get_doc("Payout Order", {"recipient": self.test_team.name})
		self.assertEqual(len(po.items), 1)

		# The invoice item must be marked as paid out
		marked_completed = frappe.db.get_value(
			"Invoice Item", po.items[0].invoice_item, "has_marketplace_payout_completed"
		)
		self.assertTrue(marked_completed)

		# Re-run should not create a new PO
		# Since all items are already accounted for
		create_marketplace_payout_orders_monthly()
		po_count = frappe.db.count("Payout Order", {"recipient": self.test_team.name})
		self.assertEqual(po_count, 1)

	def test_does_not_create_duplicate_monthly_payout_order(self):
		self.create_test_usd_invoice()

		# Create a PO for this period
		today = frappe.utils.today()
		period_start = frappe.utils.data.get_first_day(today)
		period_end = frappe.utils.data.get_last_day(today)

		# No POs initially
		num_payout_orders = frappe.db.count(
			"Payout Order", {"recipient": self.test_team.name}
		)
		self.assertEqual(num_payout_orders, 0)

		po = create_payout_order_from_invoice_items(
			[], self.test_team.name, period_start=period_start, period_end=period_end
		)

		create_marketplace_payout_orders_monthly()

		num_payout_orders = frappe.db.count(
			"Payout Order", {"recipient": self.test_team.name}
		)
		self.assertEqual(num_payout_orders, 1)

		# The original PO must now contain the invoice item
		po.reload()
		self.assertEqual(len(po.items), 1)

		# The item should be the one in the invoice
		# The invoice item must be marked as paid out
		marked_completed = frappe.db.get_value(
			"Invoice Item", po.items[0].invoice_item, "has_marketplace_payout_completed"
		)
		self.assertTrue(marked_completed)
