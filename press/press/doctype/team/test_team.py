# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import Mock, patch

import frappe
from frappe.tests.ui_test_helpers import create_test_user

from press.press.doctype.account_request.test_account_request import (
	create_test_account_request,
)
from press.press.doctype.team.team import Team


def create_test_press_admin_team(email: str = None) -> Team:
	"""Create test press admin user."""
	if not email:
		email = frappe.mock("email")
	create_test_user(email)
	user = frappe.get_doc("User", {"email": email})
	user.remove_roles(*frappe.get_all("Role", pluck="name"))
	user.add_roles("Press Admin")
	return create_test_team(email)


@patch.object(Team, "update_billing_details_on_frappeio", new=Mock())
@patch.object(Team, "create_stripe_customer", new=Mock())
def create_test_team(email: str = None, country="India") -> Team:
	"""Create test team doc."""
	if not email:
		email = frappe.mock("email")
	create_test_user(email)  # ignores if user already exists
	user = frappe.get_value("User", {"email": email}, "name")
	team = frappe.get_doc(
		{"doctype": "Team", "user": user, "enabled": 1, "country": country}
	).insert(ignore_if_duplicate=True)
	team.reload()
	return team


class TestTeam(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_new_method_works(self):
		account_request = create_test_account_request("testsubdomain")
		team_count_before = frappe.db.count("Team")
		with patch.object(Team, "create_stripe_customer"), patch.object(
			Team, "has_partner_account_on_erpnext_com"
		):
			Team.create_new(
				account_request, "first name", "last name", "test@email.com", country="India"
			)
		team_count_after = frappe.db.count("Team")
		self.assertGreater(team_count_after, team_count_before)

	def test_new_team_has_correct_billing_name(self):
		account_request = create_test_account_request("testsubdomain")
		with patch.object(Team, "create_stripe_customer"), patch.object(
			Team, "has_partner_account_on_erpnext_com"
		):
			team = Team.create_new(
				account_request, "first name", "last name", "test@email.com", country="India"
			)
		self.assertEqual(team.billing_name, "first name last name")

	def test_create_user_for_member_adds_team_member(self):
		# create system manager to pass mandatory site requirement
		Team.create_user("sys_mgr", email="testuser1@gmail.com", role="System Manager")

		team = create_test_team()
		email = "testuser@frappe.cloud"
		team.create_user_for_member("test", "user", "testuser@frappe.cloud")
		self.assertTrue(
			team.has_member(email)
		)  # kinda dumb because we assume has_member method is correct
