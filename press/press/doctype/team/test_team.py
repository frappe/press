# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.ui_test_helpers import create_test_user
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from press.press.doctype.account_request.test_account_request import (
	create_test_account_request,
)
from press.press.doctype.team.team import Team


def allow_server_creation(team: Team):
	"""Give a team the billing address and entitlement a server purchase needs."""
	address = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": team.name,
			"address_type": "Billing",
			"address_line1": "1 Test Street",
			"city": "Mumbai",
			"state": "Maharashtra",
			"gstin": "Not Applicable",
			"country": team.country,
		}
	).insert(ignore_permissions=True)

	team.db_set({"billing_address": address.name, "servers_enabled": 1})
	team.reload()


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

	def test_switching_to_card_payment_mode_moves_beginner_team_to_growth_tier(self):
		team = create_test_team()
		frappe.db.set_value(
			"Team",
			team.name,
			{"apply_limits": 1, "tier": "Beginner", "spending_limit": 100, "payment_mode": "Prepaid Credits"},
		)
		frappe.get_doc(
			{
				"doctype": "Stripe Payment Method",
				"team": team.name,
				"stripe_customer_id": "cus_test123",
				"stripe_payment_method_id": "pm_test123",
			}
		).insert(ignore_permissions=True)

		team.reload()
		team.payment_mode = "Card"
		team.save()

		self.assertEqual(frappe.db.get_value("Team", team.name, "tier"), "Growth")
		self.assertEqual(frappe.db.get_value("Team", team.name, "spending_limit"), 250)

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


class TestCreditTransfer(FrappeTestCase):
	def setUp(self):
		self.sender = create_test_team("sender@example.com")
		self.recipient = create_test_team("recipient@example.com")

	def tearDown(self):
		frappe.db.rollback()

	def test_transfer_credits_moves_prepaid_credits_to_the_recipient_team(self):
		self.sender.allocate_credit_amount(100, source="Prepaid Credits")

		self.sender.transfer_credits(60, self.recipient.user)

		self.assertEqual(self.sender.get_balance(), 40)
		self.assertEqual(self.recipient.get_balance(), 60)

	def test_transfer_credits_leaves_free_credits_with_the_team_they_were_given_to(self):
		self.sender.allocate_credit_amount(100, source="Free Credits")
		self.sender.allocate_credit_amount(50, source="Prepaid Credits")

		self.sender.transfer_credits(50, self.recipient.user)

		self.assertEqual(self.sender.get_transferable_credits(), 0)
		self.assertEqual(self.sender.get_balance(), 100)
		self.assertRaisesRegex(
			frappe.ValidationError,
			"You can transfer at most",
			self.sender.transfer_credits,
			10,
			self.recipient.user,
		)

	def test_transfer_credits_rejects_an_amount_above_the_transferable_credits(self):
		self.sender.allocate_credit_amount(100, source="Prepaid Credits")

		self.assertRaisesRegex(
			frappe.ValidationError,
			"You can transfer at most",
			self.sender.transfer_credits,
			101,
			self.recipient.user,
		)
		self.assertEqual(self.recipient.get_balance(), 0)

	def test_transfer_credits_rejects_a_recipient_billed_in_another_currency(self):
		self.sender.allocate_credit_amount(100, source="Prepaid Credits")
		foreign_team = create_test_team("foreign@example.com", country="Germany")

		self.assertRaisesRegex(
			frappe.ValidationError,
			"billed in USD",
			self.sender.transfer_credits,
			10,
			foreign_team.user,
		)

	def test_transfer_credits_rejects_a_transfer_to_the_senders_own_team(self):
		self.sender.allocate_credit_amount(100, source="Prepaid Credits")

		self.assertRaisesRegex(
			frappe.ValidationError,
			"your own account",
			self.sender.transfer_credits,
			10,
			self.sender.user,
		)

	def test_transfer_credits_rejects_an_unknown_recipient(self):
		self.sender.allocate_credit_amount(100, source="Prepaid Credits")

		self.assertRaisesRegex(
			frappe.ValidationError,
			"No active Frappe Cloud account",
			self.sender.transfer_credits,
			10,
			"nobody@example.com",
		)

	def test_transfer_credits_is_blocked_by_an_unpaid_invoice(self):
		self.sender.allocate_credit_amount(100, source="Prepaid Credits")
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=self.sender.name,
			type="Subscription",
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()
		frappe.db.set_value("Invoice", invoice.name, "status", "Unpaid")

		self.assertRaisesRegex(
			frappe.ValidationError,
			"settle your unpaid invoices",
			self.sender.transfer_credits,
			10,
			self.recipient.user,
		)

	def test_transfer_credits_ignores_the_current_months_draft_invoice(self):
		self.sender.allocate_credit_amount(100, source="Prepaid Credits")
		frappe.get_doc(
			doctype="Invoice",
			team=self.sender.name,
			type="Subscription",
			period_start=today(),
			period_end=add_days(today(), 10),
		).insert()
		# Well past the amount that counts as an unsettled invoice.
		usage_record = frappe.get_doc(doctype="Usage Record", team=self.sender.name, amount=5000)
		usage_record.insert()
		usage_record.submit()

		self.sender.transfer_credits(100, self.recipient.user)

		self.assertEqual(self.recipient.get_balance(), 100)

	def test_transfer_credits_to_a_team_that_has_no_payment_mode(self):
		# Receiving credits sets the payment mode, which reads the recipient's
		# payment methods. Run as a dashboard user, who holds only Press User.
		sender = create_test_press_admin_team("press-user-sender@example.com")
		sender.allocate_credit_amount(100, source="Prepaid Credits")
		self.assertFalse(self.recipient.payment_mode)

		frappe.set_user(sender.user)
		try:
			sender.transfer_credits(100, self.recipient.user)
		finally:
			frappe.set_user("Administrator")

		self.recipient.reload()
		self.assertEqual(self.recipient.get_balance(), 100)
		self.assertEqual(self.recipient.payment_mode, "Prepaid Credits")
