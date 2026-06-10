# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from press.partner.doctype.partner_onboarding.partner_onboarding import has_partner_onboarding
from press.press.doctype.team.test_team import create_test_team

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]


class IntegrationTestPartnerOnboarding(IntegrationTestCase):
	"""
	Integration tests for PartnerOnboarding.
	Use this class for testing interactions between multiple components.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def _create_onboarding(self, team: str, status: str = "Draft"):
		return frappe.get_doc(
			{
				"doctype": "Partner Onboarding",
				"team": team,
				"status": status,
			}
		).insert(ignore_permissions=True)

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
