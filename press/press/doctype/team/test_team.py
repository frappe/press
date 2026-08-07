# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.account_request.test_account_request import (
	create_test_account_request,
)
from press.press.doctype.team.team import Team


def create_test_press_admin_team(
	email: str | None = None, skip_onboarding: bool | None = 0, free_account: bool | None = None
) -> Team:
	"""Create test press admin user."""
	if not email:
		email = frappe.mock("email")
	create_test_user(email)
	user = frappe.get_doc("User", {"email": email})
	user.remove_roles(*frappe.get_all("Role", pluck="name"))
	user.add_roles("Press User")
	return create_test_team(email, skip_onboarding=skip_onboarding, free_account=free_account)


@patch.object(Team, "update_billing_details_on_frappeio", new=Mock())
@patch.object(Team, "create_stripe_customer", new=Mock())
def create_test_team(
	email: str | None = None,
	country="India",
	free_account: bool | None = None,
	skip_onboarding: bool | None = None,
) -> Team:
	"""Create test team doc."""
	if not email:
		email = frappe.mock("email")
	create_test_user(email)  # ignores if user already exists
	user = frappe.get_value("User", {"email": email}, "name")
	team = frappe.get_doc(
		{
			"doctype": "Team",
			"user": user,
			"enabled": 1,
			"country": country,
			"free_account": free_account,
			"skip_onboarding": skip_onboarding,
		}
	).insert(ignore_if_duplicate=True)
	team.reload()
	# Create a fake account request
	create_test_account_request(frappe.mock("name"), email=email)
	return team


class TestTeam(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_new_method_works(self):
		account_request = create_test_account_request("testsubdomain")
		team_count_before = frappe.db.count("Team")
		with patch.object(Team, "create_stripe_customer"):
			Team.create_new(account_request, "first name", "last name", "test@email.com", country="India")
		team_count_after = frappe.db.count("Team")
		self.assertGreater(team_count_after, team_count_before)

	def test_new_team_has_correct_billing_name(self):
		account_request = create_test_account_request("testsubdomain")
		with patch.object(Team, "create_stripe_customer"):
			team = Team.create_new(
				account_request, "first name", "last name", "test@email.com", country="India"
			)
		self.assertEqual(team.billing_name, "first name last name")

	def test_create_user_for_member_adds_team_member(self):
		Team.create_user("sys_mgr", email="testuser1@gmail.com")
		team = create_test_team()
		email = "testuser@frappe.cloud"
		team.create_user_for_member("test", "user", "testuser@frappe.cloud")
		self.assertTrue(team.has_member(email))  # kinda dumb because we assume has_member method is correct

	def test_new_team_has_correct_currency_set(self):
		account_request1 = create_test_account_request("testsubdomain")
		with patch.object(Team, "create_stripe_customer"):
			team1 = Team.create_new(account_request1, "Jon", "Doe", "test@gmail.com", country="India")
		self.assertEqual(team1.currency, "INR")

		account_request2 = create_test_account_request("testsubdomain2")
		with patch.object(Team, "create_stripe_customer"):
			team2 = Team.create_new(
				account_request2, "John", "Meyer", "jonmeyer@gmail.com", country="Pakistan"
			)
		self.assertEqual(team2.currency, "USD")

	def test_total_subscribed_amount_skips_legacy_subscriptions_with_null_plan_fields(self):
		team = create_test_team()
		plan = frappe.get_doc(
			{
				"doctype": "Site Plan",
				"name": "Test-Plan-USD-50",
				"document_type": "Site",
				"interval": "Daily",
				"price_usd": 50,
				"price_inr": 3000,
			}
		).insert()

		def make_sub(todo_desc):
			todo = frappe.get_doc(doctype="ToDo", description=todo_desc).insert()
			return frappe.get_doc(
				{
					"doctype": "Subscription",
					"document_type": "ToDo",
					"document_name": todo.name,
					"team": team.name,
					"plan_type": "Site Plan",
					"plan": plan.name,
					"enabled": 1,
				}
			).insert()

		make_sub("valid")

		null_plan_type_sub = make_sub("null plan_type")
		frappe.db.set_value("Subscription", null_plan_type_sub.name, "plan_type", None)

		null_plan_sub = make_sub("null plan")
		frappe.db.set_value("Subscription", null_plan_sub.name, "plan", None)

		total = team.total_subscribed_amount()
		self.assertEqual(total, 50)

	def test_get_upcoming_invoice_returns_unpaid_invoice_for_current_period(self):
		"""An invoice that has already been finalized to Unpaid (but not yet submitted) still
		owns its period - get_upcoming_invoice must not overlook it and cause a duplicate."""
		team = create_test_team()
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), -10),
			period_end=frappe.utils.add_days(frappe.utils.today(), 10),
		).insert()
		invoice.db_set("status", "Unpaid")

		self.assertEqual(team.get_upcoming_invoice().name, invoice.name)

	def test_get_upcoming_invoice_ignores_cancelled_invoice(self):
		team = create_test_team()
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), -10),
			period_end=frappe.utils.add_days(frappe.utils.today(), 10),
		).insert()
		frappe.db.set_value("Invoice", invoice.name, "docstatus", 2)

		self.assertIsNone(team.get_upcoming_invoice())

	def test_get_upcoming_invoice_matches_invoice_for_given_date_not_only_today(self):
		team = create_test_team()
		last_months_invoice = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			period_start=frappe.utils.add_days(frappe.utils.today(), -40),
			period_end=frappe.utils.add_days(frappe.utils.today(), -10),
		).insert()

		backfilled_date = frappe.utils.add_days(frappe.utils.today(), -20)

		self.assertEqual(team.get_upcoming_invoice(backfilled_date).name, last_months_invoice.name)
		self.assertIsNone(team.get_upcoming_invoice())

	def test_create_upcoming_invoice_uses_given_date_as_period_start(self):
		team = create_test_team()
		backfilled_date = frappe.utils.add_days(frappe.utils.today(), -20)

		invoice = team.create_upcoming_invoice(backfilled_date)

		self.assertEqual(frappe.utils.getdate(invoice.period_start), frappe.utils.getdate(backfilled_date))

	def test_create_upcoming_invoice_returns_existing_invoice_on_race_duplicate(self):
		"""If two callers race to create the invoice for the same date, the loser must get
		back the winner's invoice instead of raising a DuplicateEntryError."""
		team = create_test_team()
		date = frappe.utils.today()
		first = team.create_upcoming_invoice(date)

		second = team.create_upcoming_invoice(date)

		self.assertEqual(second.name, first.name)
