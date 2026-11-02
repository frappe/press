# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.account_request.test_account_request import create_test_account_request
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.team.test_team import create_test_team
from press.press.doctype.team.test_team_members import add_team_member
from press.press.report.customer_emails.customer_emails import REGIONS, execute


def get_emails(region: str) -> dict[str, dict]:
	_, rows = execute({"region": region})
	return {row["email"]: row for row in rows}


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestCustomerEmails(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_eu_team_owner_is_in_eu_report_and_not_in_non_eu_report(self):
		team = create_test_team(country="Germany")

		self.assertIn(team.user, get_emails("EU customers"))
		self.assertNotIn(team.user, get_emails("Non-EU customers"))

	def test_team_without_country_uses_the_country_of_its_signup(self):
		team = create_test_team(country=None)
		signup = frappe.get_last_doc("Account Request", {"email": team.user})
		signup.db_set("country", "Czechia")
		team.db_set("account_request", signup.name)

		self.assertIn(team.user, get_emails("EU customers"))

	def test_customer_with_no_known_country_is_non_eu(self):
		team = create_test_team(country=None)

		self.assertIn(team.user, get_emails("Non-EU customers"))
		self.assertNotIn(team.user, get_emails("EU customers"))

	def test_email_in_an_eu_and_a_non_eu_team_is_only_in_eu_report(self):
		eu_team = create_test_team(country="France")
		india_team = create_test_team(country="India")
		add_team_member(india_team.name, eu_team.user)

		self.assertIn(eu_team.user, get_emails("EU customers"))
		self.assertNotIn(eu_team.user, get_emails("Non-EU customers"))

	def test_team_notification_email_is_included_with_the_team_country(self):
		team = create_test_team(country="Spain")
		team.append(
			"communication_infos", {"channel": "Email", "type": "Billing", "value": "Billing@Example.com"}
		)
		team.save()

		self.assertEqual(get_emails("EU customers")["billing@example.com"]["teams"], team.name)

	def test_owner_of_team_with_active_site_is_listed_before_inactive_customers(self):
		active_team = create_test_team()
		create_test_site(team=active_team.name)
		inactive_team = create_test_team()

		rows = execute({"region": "All customers"})[1]
		emails = [row["email"] for row in rows]

		self.assertEqual(get_emails("All customers")[active_team.user]["customer_type"], "Active")
		self.assertEqual(get_emails("All customers")[inactive_team.user]["customer_type"], "Inactive")
		self.assertLess(emails.index(active_team.user), emails.index(inactive_team.user))

	def test_person_who_signed_up_but_never_made_a_team_is_a_signup(self):
		signup = create_test_account_request("signup-only", email="signup-only@example.com")

		self.assertEqual(get_emails("All customers")[signup.email]["customer_type"], "Signup")

	def test_deleted_team_and_its_leftover_signup_are_left_out(self):
		team = create_test_team()
		signup = frappe.get_last_doc("Account Request", {"email": team.user})
		team.db_set("account_request", signup.name)
		request = frappe.get_doc({"doctype": "Team Deletion Request", "team": team.name, "status": "Deleted"})
		request.name = "deleted-team-test@deleted.com"
		request.db_insert()

		self.assertNotIn(team.user, get_emails("All customers"))

	def test_region_filter_options_match_the_regions_in_code(self):
		report = frappe.get_doc("Report", "Customer Emails")
		options = report.filters[0].options.strip().split("\n")

		self.assertEqual(options, list(REGIONS))

	def test_unknown_region_is_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Select a Region"):
			execute({"region": "Mars customers"})
