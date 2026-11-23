# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""A partner moves credits to its customers and reads their billing."""

from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from press.api.partner import get_invoice_items, get_partner_customers, transfer_credits
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.team import Team
from press.press.doctype.team.test_team import create_test_team

PARTNER_EMAIL = "partner@example.com"


def create_partner() -> Team:
	partner = create_test_team()
	partner.db_set({"erpnext_partner": 1, "partner_status": "Active", "partner_email": PARTNER_EMAIL})
	return partner


def create_customer(partner_email: str | None = PARTNER_EMAIL) -> Team:
	customer = create_test_team()
	customer.db_set("partner_email", partner_email)
	return customer


def create_invoice(team: Team) -> Invoice:
	site = create_test_site(team=team.name)
	invoice = frappe.get_doc(
		doctype="Invoice", team=team.name, period_start=today(), period_end=add_days(today(), 10)
	)
	invoice.append(
		"items",
		{"document_type": "Site", "document_name": site.name, "quantity": 1, "rate": 100, "amount": 100},
	)
	return invoice.insert()


# frappe.io reports the partner level, which sets the partner's discount
@patch.object(Team, "get_partner_level", new=Mock(return_value=["Gold"]))
@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
# transfer_credits commits, which would leak records past the rollback
@patch("press.api.partner.frappe.db.commit", new=Mock())
class TestPartnerCredits(FrappeTestCase):
	def setUp(self):
		self.partner = create_partner()
		self.partner.allocate_credit_amount(1000, source="Prepaid Credits")
		self.customer = create_customer()
		frappe.set_user(self.partner.user)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def balance(self, team: Team) -> float:
		return Team("Team", team.name).get_balance()

	def test_transfer_gives_the_customer_the_full_amount_and_charges_the_partner_less_its_discount(self):
		transfer_credits(100, self.customer.name)

		self.assertEqual(self.balance(self.customer), 100)
		self.assertEqual(self.balance(self.partner), 1000 - 75)

	def test_transfer_of_more_than_the_partners_balance_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Insufficient Credits"):
			transfer_credits(5000, self.customer.name)

		self.assertEqual(self.balance(self.customer), 0)

	def test_transfer_of_a_negative_amount_is_refused_and_moves_no_credits(self):
		self.customer.allocate_credit_amount(500, source="Prepaid Credits")

		with self.assertRaisesRegex(frappe.ValidationError, "more than 0"):
			transfer_credits(-500, self.customer.name)

		self.assertEqual((self.balance(self.partner), self.balance(self.customer)), (1000, 500))

	def test_transfer_by_a_team_that_is_not_a_partner_is_refused(self):
		self.partner.db_set({"erpnext_partner": 0, "partner_status": ""})

		with self.assertRaisesRegex(frappe.ValidationError, "Only an active partner team"):
			transfer_credits(100, self.customer.name)

		self.assertEqual(self.balance(self.customer), 0)


@patch.object(Invoice, "create_invoice_on_frappeio", new=Mock())
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestPartnerBillingVisibility(FrappeTestCase):
	def setUp(self):
		self.partner = create_partner()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_partner_customer_list_has_only_the_partners_own_customers(self):
		own_customer = create_customer()
		create_customer(partner_email="another-partner@example.com")
		frappe.set_user(self.partner.user)

		customers = get_partner_customers()

		self.assertEqual([customer.name for customer in customers], [own_customer.name])

	def test_partner_can_read_the_items_of_its_customers_invoice(self):
		invoice = create_invoice(create_customer())
		frappe.set_user(self.partner.user)

		items = get_invoice_items(invoice.name)

		self.assertEqual([item.amount for item in items], [100])

	def test_partner_cannot_read_the_items_of_another_partners_customers_invoice(self):
		invoice = create_invoice(create_customer(partner_email="another-partner@example.com"))
		frappe.set_user(self.partner.user)

		self.assertIsNone(get_invoice_items(invoice.name))

	def test_customer_cannot_read_the_items_of_another_customer_of_the_same_partner(self):
		invoice = create_invoice(create_customer())
		frappe.set_user(create_customer().user)

		self.assertIsNone(get_invoice_items(invoice.name))

	def test_team_without_a_partner_cannot_read_the_items_of_another_teams_invoice(self):
		invoice = create_invoice(create_customer(partner_email=None))
		outsider = create_customer(partner_email=None)
		frappe.set_user(outsider.user)

		self.assertIsNone(get_invoice_items(invoice.name))
