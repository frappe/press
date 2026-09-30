# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.team.test_team import create_test_team


class TestUsageRecord(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_team()

	def tearDown(self):
		frappe.db.rollback()

	def test_late_usage_record_for_past_month_attaches_to_that_months_existing_invoice(self):
		"""A usage record created "today" but dated within an already-existing past invoice's
		period (e.g. a backfilled/late record) must attach to that invoice, not spawn a new
		one keyed off today's date."""
		past_invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), -40),
			period_end=frappe.utils.add_days(frappe.utils.today(), -10),
		).insert()

		backfilled_date = frappe.utils.add_days(frappe.utils.today(), -20)
		usage_record = frappe.get_doc(
			doctype="Usage Record", team=self.team.name, amount=42, date=backfilled_date
		)
		usage_record.insert()
		usage_record.submit()

		self.assertEqual(usage_record.invoice, past_invoice.name)
		self.assertFalse(
			frappe.db.exists(
				"Invoice",
				{"team": self.team.name, "period_start": frappe.utils.today(), "type": "Subscription"},
			)
		)

	def test_late_usage_record_against_submitted_invoice_fails_loudly_instead_of_crashing(self):
		"""Once an invoice is submitted (Paid/Empty) it can no longer be mutated. A usage
		record whose date falls in that period must fail with our own clear error, not
		leak frappe's opaque UpdateAfterSubmitError from an attempted item append."""
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.today(),
			period_end=frappe.utils.add_days(frappe.utils.today(), 10),
		).insert()
		invoice.finalize_invoice()  # total is 0 -> status Empty, submitted (docstatus=1)
		self.assertEqual(invoice.docstatus, 1)

		usage_record = frappe.get_doc(doctype="Usage Record", team=self.team.name, amount=42)
		usage_record.insert()

		with self.assertRaises(frappe.ValidationError) as context:
			usage_record.submit()
		self.assertIn("already covers this period", str(context.exception))

	def test_late_usage_record_against_unpaid_invoice_fails_loudly_instead_of_mutating_it(self):
		"""An invoice finalized to Unpaid (docstatus still 0, not yet submitted) may already
		have a Stripe/Razorpay invoice created against it. A usage record whose date falls
		in that period must fail loudly, not silently append to and re-save it."""
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.today(),
			period_end=frappe.utils.add_days(frappe.utils.today(), 10),
		).insert()
		invoice.db_set("status", "Unpaid")
		self.assertEqual(invoice.docstatus, 0)

		usage_record = frappe.get_doc(doctype="Usage Record", team=self.team.name, amount=42)
		usage_record.insert()

		with self.assertRaises(frappe.ValidationError) as context:
			usage_record.submit()
		self.assertIn("already covers this period", str(context.exception))

		invoice.reload()
		self.assertEqual(len(invoice.items), 0)

	def test_usage_record_creates_invoice_for_its_own_date_when_none_exists(self):
		backfilled_date = frappe.utils.add_days(frappe.utils.today(), -20)
		usage_record = frappe.get_doc(
			doctype="Usage Record", team=self.team.name, amount=42, date=backfilled_date
		)
		usage_record.insert()
		usage_record.submit()

		invoice = frappe.get_doc("Invoice", usage_record.invoice)
		self.assertEqual(invoice.period_start, frappe.utils.getdate(backfilled_date))

	def test_cancelling_usage_record_removes_it_from_its_linked_invoice_not_a_newer_one(self):
		"""remove_usage_from_invoice must use the usage record's own invoice link, not a
		fresh team/date lookup that could resolve to an unrelated, newer invoice."""
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.today(),
			period_end=frappe.utils.add_days(frappe.utils.today(), 10),
		).insert()

		usage_record = frappe.get_doc(doctype="Usage Record", team=self.team.name, amount=42)
		usage_record.insert()
		usage_record.submit()
		self.assertEqual(usage_record.invoice, invoice.name)

		# a newer invoice also covering "today" (e.g. next period's pre-created invoice) -
		# a naive today-based lookup in remove_usage_from_invoice would resolve to this one
		frappe.get_doc(
			doctype="Invoice",
			team=self.team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), 11),
			period_end=frappe.utils.add_days(frappe.utils.today(), 20),
		).insert()

		usage_record.cancel()
		invoice.reload()

		self.assertEqual(len(invoice.items), 0)
		self.assertIsNone(usage_record.invoice)
