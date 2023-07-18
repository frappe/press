# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import patch, Mock

import frappe
from frappe.utils.data import add_days, today

from press.press.doctype.team.test_team import create_test_team

from .invoice import Invoice


@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
class TestInvoice(unittest.TestCase):
	def setUp(self):
		self.team = create_test_team()

	def tearDown(self):
		frappe.db.rollback()

	def test_invoice_add_usage_record(self):
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		for amount in [10, 20, 30]:
			usage_record = frappe.get_doc(
				doctype="Usage Record", team=self.team.name, amount=amount
			)
			usage_record.insert()
			usage_record.submit()

		invoice.reload()

		self.assertEqual(len(invoice.items), 3)
		self.assertEqual(invoice.total, 60)

		with patch.object(invoice, "create_stripe_invoice", return_value=None):
			invoice.finalize_invoice()

		self.assertEqual(invoice.amount_due, 60)

	def test_invoice_cancel_usage_record(self):

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		usage_records = []
		for amount in [10, 20, 30, 40]:
			usage_record = frappe.get_doc(
				doctype="Usage Record", team=self.team.name, amount=amount
			)
			usage_record.insert()
			usage_record.submit()
			usage_records.append(usage_record)

		invoice.reload()

		self.assertEqual(len(invoice.items), 4)
		self.assertEqual(invoice.total, 100)

		# cancel usage record
		usage_records[0].cancel()
		invoice.reload()

		self.assertEqual(len(invoice.items), 3)
		self.assertEqual(invoice.total, 90)
		self.assertEqual(usage_records[0].invoice, None)

	def test_invoice_with_credits_less_than_total(self):

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		for amount in [10, 20, 30]:
			usage_record = frappe.get_doc(
				doctype="Usage Record", team=self.team.name, amount=amount
			)
			usage_record.insert()
			usage_record.submit()

		self.assertEqual(self.team.get_balance(), 0)
		self.team.allocate_credit_amount(10, source="Free Credits")
		self.assertEqual(self.team.get_balance(), 10)

		invoice.reload()

		with patch.object(invoice, "create_stripe_invoice", return_value=None):
			try:
				invoice.finalize_invoice()
			except Exception as e:
				self.assertEqual(
					str(e),
					"Not enough credits for this invoice. Change payment mode to Card to"
					" pay using Stripe.",
				)

		self.assertEqual(self.team.get_balance(), 0)
		self.assertEqual(invoice.total, 60)
		self.assertEqual(invoice.amount_due, 50)
		self.assertEqual(invoice.applied_credits, 10)

	def test_invoice_with_credits_more_than_total(self):

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		for amount in [10, 20, 30]:
			usage_record = frappe.get_doc(
				doctype="Usage Record", team=self.team.name, amount=amount
			)
			usage_record.insert()
			usage_record.submit()

		self.assertEqual(self.team.get_balance(), 0)
		self.team.allocate_credit_amount(70, source="Free Credits")
		self.assertEqual(self.team.get_balance(), 70)

		invoice.reload()

		with patch.object(invoice, "create_stripe_invoice", return_value=None):
			invoice.finalize_invoice()

		self.assertEqual(self.team.get_balance(), 10)
		self.assertEqual(invoice.total, 60)
		self.assertEqual(invoice.amount_due, 0)
		self.assertEqual(invoice.applied_credits, 60)

	def test_invoice_credit_allocation(self):

		# First Invoice
		# Total: 600
		# Team has 100 Free Credits and 1000 Prepaid Credits
		# Invoice can be paid using credits
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
			items=[{"quantity": 1, "rate": 600}],
		).insert()

		self.assertEqual(self.team.get_balance(), 0)
		self.team.allocate_credit_amount(100, source="Free Credits")
		self.team.allocate_credit_amount(1000, source="Prepaid Credits")
		self.assertEqual(self.team.get_balance(), 1100)
		invoice.reload()

		with patch.object(invoice, "create_stripe_invoice", return_value=None):
			invoice.finalize_invoice()

		self.assertEqual(invoice.total, 600)
		self.assertEqual(self.team.get_balance(), 1100 - 600)
		self.assertEqual(invoice.amount_due, 0)
		self.assertEqual(invoice.applied_credits, 600)
		self.assertDictContainsSubset(
			{"amount": 100, "source": "Free Credits"}, invoice.credit_allocations[0].as_dict()
		)
		self.assertDictContainsSubset(
			{"amount": 500, "source": "Prepaid Credits"}, invoice.credit_allocations[1].as_dict()
		)

		# Second Invoice
		# Total: 700
		# Team has 500 Credits left after the first invoice
		# Invoice due should be 200
		invoice2 = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=add_days(today(), 11),
			items=[{"quantity": 1, "rate": 700}],
		).insert()
		invoice2.reload()

		with patch.object(invoice2, "create_stripe_invoice", return_value=None):
			try:
				invoice2.finalize_invoice()
			except Exception as e:
				self.assertEqual(
					str(e),
					"Not enough credits for this invoice. Change payment mode to Card to"
					" pay using Stripe.",
				)

		self.assertEqual(invoice2.total, 700)
		self.assertEqual(invoice2.applied_credits, 500)
		self.assertEqual(invoice2.amount_due, 200)
		self.assertDictContainsSubset(
			{"amount": 500, "source": "Prepaid Credits"},
			invoice2.credit_allocations[0].as_dict(),
		)

	def test_invoice_cancel_reverse_credit_allocation(self):

		# First Invoice
		# Total: 600
		# Team has 100 Free Credits and 1000 Prepaid Credits
		# Invoice can be paid using credits
		self.team.allocate_credit_amount(100, source="Free Credits")
		self.team.allocate_credit_amount(1000, source="Prepaid Credits")
		self.assertEqual(self.team.get_balance(), 1100)

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
			items=[{"quantity": 1, "rate": 600}],
		).insert()

		with patch.object(invoice, "create_stripe_invoice", return_value=None):
			invoice.finalize_invoice()

		self.assertEqual(invoice.total, 600)
		self.assertEqual(self.team.get_balance(), 1100 - 600)
		self.assertEqual(invoice.amount_due, 0)
		self.assertEqual(invoice.applied_credits, 600)
		self.assertDictContainsSubset(
			{"amount": 100, "source": "Free Credits"}, invoice.credit_allocations[0].as_dict()
		)
		self.assertDictContainsSubset(
			{"amount": 500, "source": "Prepaid Credits"}, invoice.credit_allocations[1].as_dict()
		)

		# Cancel Invoice
		invoice.cancel()
		# Team balance should go back to 1100
		self.assertEqual(self.team.get_balance(), 1100)

	def test_intersecting_invoices(self):

		invoice1 = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.today(),
			period_end=frappe.utils.add_days(frappe.utils.today(), 5),
		).insert()

		invoice2 = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), 1),
			period_end=frappe.utils.add_days(frappe.utils.today(), 6),
		)

		invoice3 = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.today(),
			period_end=frappe.utils.add_days(frappe.utils.today(), 5),
		)

		invoice4 = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), -2),
			period_end=frappe.utils.add_days(frappe.utils.today(), 3),
		)

		invoice5 = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.add_days(invoice1.period_end, 1),
		)

		self.assertRaises(frappe.DuplicateEntryError, invoice2.insert)
		self.assertRaises(frappe.DuplicateEntryError, invoice3.insert)
		self.assertRaises(frappe.DuplicateEntryError, invoice4.insert)

		invoice5.insert()

	def test_prepaid_credits(self):
		from pathlib import Path

		from press.press.doctype.team.team import process_stripe_webhook

		self.team.db_set("stripe_customer_id", "cus_H3L4w6RXJPKLQs")
		# initial balance is 0
		self.assertEqual(self.team.get_balance(), 0)

		with open(
			Path(__file__).parent / "fixtures/stripe_payment_intent_succeeded_webhook.json", "r"
		) as payload:
			doc = frappe._dict(
				{"event_type": "payment_intent.succeeded", "payload": payload.read()}
			)

		with patch.object(Invoice, "update_transaction_details", return_value=None):
			process_stripe_webhook(doc, "")

		# balance should 900 after buying prepaid credits
		self.assertEqual(self.team.get_balance(), 900)

	def test_single_x_percent_flat_on_total(self):

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		invoice.append("items", {"quantity": 1, "rate": 1000, "amount": 1000})
		invoice.save()

		# Before discount
		self.assertEqual(invoice.total, 1000)

		# Apply 10% discount
		invoice.append(
			"discounts", {"percent": 10, "discount_type": "Flat On Total", "based_on": "Percent"}
		)
		invoice.save()

		# After discount
		invoice.reload()
		self.assertEqual(invoice.total_before_discount, 1000)
		self.assertEqual(invoice.total_discount_amount, 100)
		self.assertEqual(invoice.total, 900)

	def test_multiple_discounts_flat_on_total(self):

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		invoice.append("items", {"quantity": 1, "rate": 1000, "amount": 1000})
		invoice.save()

		# Apply 10% discount
		invoice.append(
			"discounts", {"percent": 10, "discount_type": "Flat On Total", "based_on": "Percent"}
		)

		# Apply another 10%
		invoice.append(
			"discounts", {"percent": 10, "discount_type": "Flat On Total", "based_on": "Percent"}
		)

		invoice.save()

		# After discount
		invoice.reload()
		self.assertEqual(invoice.total_before_discount, 1000)
		self.assertEqual(invoice.total_discount_amount, 200)
		self.assertEqual(invoice.total, 800)

	def test_discount_borrowed_from_team(self):

		# Give 30% to team
		self.team.append(
			"discounts", {"percent": 30, "discount_type": "Flat On Total", "based_on": "Percent"}
		)
		self.team.save()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		# Add line items
		invoice.append("items", {"quantity": 1, "rate": 1000, "amount": 1000})
		invoice.save()
		invoice.reload()

		# After discount
		self.assertEqual(invoice.total_before_discount, 1000)
		self.assertEqual(invoice.total_discount_amount, 300)
		self.assertEqual(invoice.total, 700)

	def test_mix_discounts_flat_on_total_and_percent(self):

		# Give 30% to team
		self.team.append(
			"discounts", {"percent": 30, "discount_type": "Flat On Total", "based_on": "Percent"}
		)
		self.team.save()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		# Add line items
		invoice.append("items", {"quantity": 1, "rate": 500, "amount": 500})
		invoice.append("items", {"quantity": 1, "rate": 500, "amount": 500})

		# Apply 100 units discount
		invoice.append(
			"discounts", {"amount": 100, "discount_type": "Flat On Total", "based_on": "Amount"}
		)

		invoice.save()
		invoice.reload()

		# After discount
		self.assertEqual(invoice.total_before_discount, 1000)
		self.assertEqual(invoice.total_discount_amount, 400)
		self.assertEqual(invoice.total, 600)

	def test_finalize_invoice_with_total_zero(self):
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		invoice.append("items", {"quantity": 1, "rate": 0, "amount": 0})
		invoice.save()
		invoice.reload()

		self.assertEqual(invoice.total, 0)

		invoice.finalize_invoice()

		# After finalize
		self.assertEqual(invoice.total, 0)
		self.assertEqual(invoice.status, "Empty")

	def test_finalize_invoice_for_disabled_team(self):
		self.team.enabled = 0
		self.team.save()

		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		invoice.append("items", {"quantity": 1, "rate": 100, "amount": 100})
		invoice.save()
		invoice.reload()

		invoice.finalize_invoice()

		self.assertEqual(invoice.status, "Draft")

	@patch("press.api.billing.get_stripe")
	def test_create_stripe_invoice_with_prepaid_credits(self, mock_stripe):
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			type="Prepaid Credits",
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()
		invoice.finalize_invoice()
		self.assertEqual(invoice.stripe_invoice_id, None)
