# Copyright (c) 2020, Frappe and Contributors
# See license.txt


from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import add_days, today

from press.press.doctype.team.test_team import create_test_team

from .invoice import Invoice


@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
class TestInvoice(FrappeTestCase):
	def assertDictContainsSubset(self, subset: dict, dictionary: dict) -> None:
		self.assertEqual(subset, dictionary | subset)

	def setUp(self):
		super().setUp()

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
			usage_record = frappe.get_doc(doctype="Usage Record", team=self.team.name, amount=amount)
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
			usage_record = frappe.get_doc(doctype="Usage Record", team=self.team.name, amount=amount)
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
			usage_record = frappe.get_doc(doctype="Usage Record", team=self.team.name, amount=amount)
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
					"Not enough credits for this invoice. Change payment mode to Card to pay using Stripe.",
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
			usage_record = frappe.get_doc(doctype="Usage Record", team=self.team.name, amount=amount)
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
					"Not enough credits for this invoice. Change payment mode to Card to pay using Stripe.",
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
			doc = frappe._dict({"event_type": "payment_intent.succeeded", "payload": payload.read()})

		with patch.object(Invoice, "update_transaction_details", return_value=None):
			process_stripe_webhook(doc, "")

		# balance should 755.64 after buying prepaid credits with gst applied
		self.assertEqual(self.team.get_balance(), 755.64)

	def test_discount_amount(self):
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		invoice.append("items", {"quantity": 1, "rate": 1000, "amount": 1000, "discount": 10})
		invoice.append("items", {"quantity": 1, "rate": 1000, "amount": 1000})
		invoice.save()
		invoice.reload()

		self.assertEqual(invoice.total_before_discount, 2000)
		self.assertEqual(invoice.total_discount_amount, 10)
		self.assertEqual(invoice.total, 2000 - 10)

	def test_discount_percentage(self):
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()

		invoice.append("items", {"quantity": 1, "rate": 1000, "amount": 1000, "discount_percentage": 10})
		invoice.append("items", {"quantity": 1, "rate": 1000, "amount": 1000})
		invoice.save()
		invoice.reload()
		self.assertEqual(invoice.items[0].discount, 100)
		self.assertEqual(invoice.total_before_discount, 2000)
		self.assertEqual(invoice.total_discount_amount, 100)
		self.assertEqual(invoice.total, 2000 - 100)

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

	def test_negative_balance_case(self):
		team = create_test_team("test22@example.com")

		# add 10 credits
		team.allocate_credit_amount(10, source="Prepaid Credits")
		# transfer 5 credits
		team.allocate_credit_amount(-5, source="Transferred Credits")
		team.payment_mode = "Prepaid Credits"
		team.save()

		# consume 10 credits
		invoice = frappe.get_doc(doctype="Invoice", team=team.name)
		invoice.append("items", {"quantity": 1, "rate": 10, "amount": 10})
		invoice.insert()

		# finalize invoice
		invoice.finalize_invoice()
		self.assertTrue(invoice.status == "Unpaid")
		self.assertTrue(invoice.amount_due > 0)

	def test_negative_balance_case_2(self):
		team = create_test_team("test22@example.com")
		team.allocate_credit_amount(10, source="Prepaid Credits")

		invoice = frappe.get_doc(doctype="Invoice", team=team.name)
		invoice.append("items", {"quantity": 1, "rate": 8, "amount": 8})
		invoice.insert()
		invoice.finalize_invoice()

		with self.assertRaises(frappe.ValidationError) as err:
			team.allocate_credit_amount(-5, source="Transferred Credits")
		self.assertTrue("is less than" in str(err.exception))

	def test_negative_balance_allocation(self):
		team = create_test_team("test22@example.com")
		team.allocate_credit_amount(10, source="Prepaid Credits")
		team.allocate_credit_amount(30, source="Prepaid Credits")

		with self.assertRaises(frappe.ValidationError) as err:
			team.allocate_credit_amount(-50, source="Transferred Credits")
		self.assertTrue("is less than" in str(err.exception))

		team.allocate_credit_amount(-35, source="Transferred Credits")
		self.assertEqual(team.get_balance(), 5)
		transactions = frappe.get_all(
			"Balance Transaction",
			filters={
				"team": team.name,
				"docstatus": 1,
				"unallocated_amount": (">=", 0),
				"source": "Prepaid Credits",
			},
			fields=["name", "unallocated_amount"],
			order_by="creation asc",
		)
		self.assertEqual(len(transactions), 2)
		self.assertEqual(transactions[0].unallocated_amount, 0)
		self.assertEqual(transactions[1].unallocated_amount, 5)

	def test_settle_negative_balance(self):
		# create team
		# allocate -100 credits
		# try to settle by adding 200 credits
		# the new unallocated amount should be 100

		team = create_test_team("test22@example.com")
		bt = frappe.new_doc("Balance Transaction")
		bt.team = team.name
		bt.amount = -100
		bt.source = "Transferred Credits"
		bt.type = "Adjustment"
		bt.docstatus = 1
		bt.db_insert()

		settling_transaction = team.allocate_credit_amount(200, source="Prepaid Credits")
		self.assertEqual(team.get_balance(), 100)

		settling_transaction.reload()
		self.assertEqual(settling_transaction.unallocated_amount, 100)

	def test_invoice_for_update_after_submit_error(self):
		team = create_test_team("jondoe@example.com")
		team.allocate_credit_amount(10, source="Free Credits")
		team.payment_mode = "Prepaid Credits"
		team.save()

		invoice = frappe.new_doc("Invoice", team=team.name)
		invoice.append("items", {"quantity": 5, "rate": 0.33, "amount": 1.65})
		invoice.append("items", {"quantity": 3, "rate": 2, "amount": 6, "discount_percentage": 10})
		invoice.insert()
		invoice.finalize_invoice()  # finalize invoice submits the doc if invoice gets settled
		self.assertEqual(invoice.status, "Paid")

		before_total = invoice.total
		before_total_before_discount = invoice.total_before_discount
		before_total_discount_amount = invoice.total_discount_amount
		invoice.validate()
		invoice.save()
		invoice.reload()

		after_total = invoice.total
		after_total_before_discount = invoice.total_before_discount
		after_total_discount_amount = invoice.total_discount_amount
		self.assertEqual(before_total, after_total)
		self.assertEqual(before_total_before_discount, after_total_before_discount)
		self.assertEqual(before_total_discount_amount, after_total_discount_amount)

	def test_tax_without_credits(self):
		team = create_test_team("tax_without_credits@example.com")
		frappe.db.set_single_value("Press Settings", "gst_percentage", 0.18)

		invoice = frappe.get_doc(doctype="Invoice", team=team.name)
		invoice.append("items", {"quantity": 1, "rate": 10, "amount": 10})
		invoice.insert()

		invoice.finalize_invoice()
		self.assertEqual(invoice.amount_due, 10)
		self.assertEqual(invoice.amount_due_with_tax, 11.8)

	def test_tax_with_credits(self):
		"""Test invoice with tax when payment mode is prepaid credits"""
		team = create_test_team("tax_with_credits@example.com")
		team.allocate_credit_amount(5, source="Prepaid Credits")
		frappe.db.set_single_value("Press Settings", "gst_percentage", 0.18)

		invoice = frappe.get_doc(doctype="Invoice", team=team.name)
		invoice.append("items", {"quantity": 1, "rate": 10, "amount": 10})
		invoice.insert()

		invoice.finalize_invoice()
		self.assertEqual(invoice.total, 10)
		self.assertEqual(invoice.applied_credits, 5)
		self.assertEqual(invoice.amount_due, 5)
		self.assertEqual(invoice.amount_due_with_tax, 5)

	@patch.object(Invoice, "create_stripe_invoice", new=Mock())
	def test_tax_with_credits_with_card(self):
		"""Test invoice with tax when payment mode is card"""
		team = create_test_team("tax_with_credits@example.com")
		team.allocate_credit_amount(5, source="Prepaid Credits")
		frappe.db.set_value("Team", team.name, "payment_mode", "Card")
		# team.reload()
		frappe.db.set_single_value("Press Settings", "gst_percentage", 0.18)

		invoice = frappe.get_doc(doctype="Invoice", team=team.name)
		invoice.append("items", {"quantity": 1, "rate": 10, "amount": 10})
		invoice.insert()

		invoice.finalize_invoice()
		self.assertEqual(invoice.total, 10)
		self.assertEqual(invoice.applied_credits, 5)
		self.assertEqual(invoice.amount_due, 5)
		self.assertEqual(invoice.amount_due_with_tax, 5.9)

	def test_tax_for_usd_accounts(self):
		team = create_test_team("tax_for_usd_accounts@example.com", "United States")
		frappe.db.set_single_value("Press Settings", "gst_percentage", 0.18)

		invoice = frappe.get_doc(doctype="Invoice", team=team.name)
		invoice.append("items", {"quantity": 1, "rate": 10, "amount": 10})
		invoice.insert()

		invoice.finalize_invoice()
		self.assertEqual(invoice.total, 10)
		self.assertEqual(invoice.amount_due, 10)
		self.assertEqual(invoice.amount_due_with_tax, 10)

	def test_npo_discount(self):
		team = create_test_team("npo_team_discount@gmail.com")
		team.apply_npo_discount = 1
		team.save()
		frappe.db.set_single_value("Press Settings", "npo_discount", 10)

		invoice = frappe.get_doc(doctype="Invoice", team=team.name)
		invoice.append("items", {"quantity": 1, "rate": 100, "amount": 100})
		invoice.insert()

		invoice.finalize_invoice()
		self.assertEqual(invoice.total, 90)
		self.assertEqual(invoice.total_before_discount, 100)
		self.assertEqual(invoice.total_discount_amount, 10)
		self.assertEqual(invoice.amount_due, 90)
