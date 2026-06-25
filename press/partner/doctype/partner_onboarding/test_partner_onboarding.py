# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_months, get_last_day, today

from press.partner.doctype.partner_onboarding.partner_onboarding import (
	_get_mrr_status,
	has_partner_onboarding,
)
from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.team.test_team import create_test_team
from press.tests.before_test import freeze_time

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]

# Fixed dates drive month-position branching in _get_mrr_subscription_invoices
# deterministically once a team has more than one subscription invoice.
AFTER_MID_MONTH = "2026-01-20"
BEFORE_MID_MONTH = "2026-01-10"


@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
class IntegrationTestPartnerOnboarding(IntegrationTestCase):
	"""
	Integration tests for PartnerOnboarding.
	Use this class for testing interactions between multiple components.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def _create_onboarding(self, team: str, status: str = "Draft"):
		# The Register Company modal collects these four fields on first
		# registration, so they are mandatory at creation. Supply them here
		# to mirror a real draft record.
		return frappe.get_doc(
			{
				"doctype": "Partner Onboarding",
				"team": team,
				"status": status,
				"company_name": "Test Partner Company",
				"registered_country": "India",
				"company_email": "partner@example.com",
				"contact": "+919876543210",
			}
		).insert(ignore_permissions=True)

	def _create_subscription_invoice(
		self,
		team: str,
		due_date: str,
		amount: float,
		status: str = "Unpaid",
		submitted: bool = False,
	):
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team,
			type="Subscription",
			due_date=due_date,
			status=status,
			items=[{"quantity": 1, "rate": amount}],
		).insert()
		if submitted:
			# Paid Subscription invoices are submitted in production, but the
			# "Invoice must be Paid to be submitted" guard makes a normal submit
			# awkward in tests — force the persisted state the query reads.
			frappe.db.set_value(
				"Invoice", invoice.name, {"status": status, "docstatus": 1}, update_modified=False
			)
		return invoice

	def _seed_prior_subscription_invoice(self, team: str):
		"""Add a second Subscription invoice so MRR uses last-month cycle logic."""
		prior_due = get_last_day(add_months(today(), -2))
		self._create_subscription_invoice(team, prior_due, 1000, status="Paid", submitted=True)

	def test_has_partner_onboarding_is_false_without_a_record(self):
		team = create_test_team()
		self.assertFalse(has_partner_onboarding(team.name))

	def test_has_partner_onboarding_is_true_with_a_draft_record(self):
		team = create_test_team()
		self._create_onboarding(team.name)
		self.assertTrue(has_partner_onboarding(team.name))

	def test_has_partner_onboarding_ignores_cancelled_records(self):
		team = create_test_team()
		onboarding = self._create_onboarding(team.name)
		onboarding.db_set("status", "Cancelled")
		self.assertFalse(has_partner_onboarding(team.name))

	def test_mrr_first_billing_month_counts_current_month_invoice(self):
		"""With only one subscription invoice, the current month cycle is used."""
		team = create_test_team()
		with freeze_time(BEFORE_MID_MONTH):
			self._create_subscription_invoice(team.name, get_last_day(today()), 12000, status="Unpaid")
			status = _get_mrr_status(team)

		self.assertEqual(status["currency"], "INR")
		self.assertEqual(status["target_amount"], 10000)
		self.assertEqual(status["current_amount"], 12000)
		self.assertTrue(status["requirement_complete"])

	def test_mrr_first_billing_month_below_threshold(self):
		team = create_test_team()
		with freeze_time(AFTER_MID_MONTH):
			self._create_subscription_invoice(team.name, get_last_day(today()), 5000, status="Unpaid")
			status = _get_mrr_status(team)

		self.assertEqual(status["current_amount"], 5000)
		self.assertFalse(status["requirement_complete"])

	def test_mrr_first_billing_month_ignores_prior_month_only_invoice(self):
		team = create_test_team()
		with freeze_time(AFTER_MID_MONTH):
			last_month_due = get_last_day(add_months(today(), -1))
			self._create_subscription_invoice(team.name, last_month_due, 12000, status="Paid", submitted=True)
			status = _get_mrr_status(team)

		self.assertEqual(status["current_amount"], 0)
		self.assertFalse(status["requirement_complete"])

	def test_mrr_after_mid_month_uses_last_month_paid_invoice(self):
		team = create_test_team()
		with freeze_time(AFTER_MID_MONTH):
			self._seed_prior_subscription_invoice(team.name)
			last_month_due = get_last_day(add_months(today(), -1))
			self._create_subscription_invoice(team.name, last_month_due, 12000, status="Paid", submitted=True)
			status = _get_mrr_status(team)

		self.assertEqual(status["current_amount"], 12000)
		self.assertTrue(status["requirement_complete"])

	def test_mrr_after_mid_month_ignores_last_month_unpaid_invoice(self):
		team = create_test_team()
		with freeze_time(AFTER_MID_MONTH):
			self._seed_prior_subscription_invoice(team.name)
			last_month_due = get_last_day(add_months(today(), -1))
			self._create_subscription_invoice(team.name, last_month_due, 12000, status="Unpaid")
			status = _get_mrr_status(team)

		self.assertEqual(status["current_amount"], 0)
		self.assertFalse(status["requirement_complete"])

	def test_mrr_after_mid_month_ignores_current_month_invoice(self):
		team = create_test_team()
		with freeze_time(AFTER_MID_MONTH):
			self._seed_prior_subscription_invoice(team.name)
			self._create_subscription_invoice(team.name, get_last_day(today()), 12000, status="Unpaid")
			status = _get_mrr_status(team)

		self.assertEqual(status["current_amount"], 0)
		self.assertFalse(status["requirement_complete"])

	def test_mrr_before_mid_month_uses_last_month_paid_invoice(self):
		team = create_test_team()
		with freeze_time(BEFORE_MID_MONTH):
			self._seed_prior_subscription_invoice(team.name)
			last_month_due = get_last_day(add_months(today(), -1))
			self._create_subscription_invoice(team.name, last_month_due, 12000, status="Paid", submitted=True)
			status = _get_mrr_status(team)

		self.assertEqual(status["current_amount"], 12000)
		self.assertTrue(status["requirement_complete"])

	def test_mrr_before_mid_month_counts_unpaid_last_month_invoice(self):
		team = create_test_team()
		with freeze_time(BEFORE_MID_MONTH):
			self._seed_prior_subscription_invoice(team.name)
			last_month_due = get_last_day(add_months(today(), -1))
			self._create_subscription_invoice(team.name, last_month_due, 12000, status="Unpaid")
			status = _get_mrr_status(team)

		self.assertEqual(status["current_amount"], 12000)
		self.assertTrue(status["requirement_complete"])

	def test_mrr_before_mid_month_ignores_current_month_invoice(self):
		team = create_test_team()
		with freeze_time(BEFORE_MID_MONTH):
			self._seed_prior_subscription_invoice(team.name)
			self._create_subscription_invoice(team.name, get_last_day(today()), 12000, status="Unpaid")
			status = _get_mrr_status(team)

		self.assertEqual(status["current_amount"], 0)
		self.assertFalse(status["requirement_complete"])
