# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import unittest
from unittest.mock import patch

import frappe

from press.press.doctype.account_request.test_account_request import (
	create_test_account_request,
)
from press.press.doctype.team.team import Team


def create_test_team(email: str = frappe.mock("email")):
	"""Create test team doc."""
	return frappe.get_doc({"doctype": "Team", "name": email}).insert(
		ignore_if_duplicate=True
	)


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
