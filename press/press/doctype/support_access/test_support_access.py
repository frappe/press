# Copyright (c) 2025, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.support_access.support_access import SupportAccess, expire_pending_requests
from press.press.doctype.team.test_team import create_test_press_admin_team

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class UnitTestSupportAccess(UnitTestCase):
	"""
	Unit tests for SupportAccess.
	Use this class for testing individual functions and methods.
	"""

	def test_valid_status_transition(self):
		combinations = [
			["Pending", "Accepted", True],
			["Pending", "Rejected", True],
			["Accepted", "Revoked", True],
			["Accepted", "Forfeited", True],
			["Rejected", "Accepted", False],
			["Forfeited", "Accepted", False],
			["Revoked", "Accepted", False],
			["Pending", "Forfeited", False],
			["Pending", "Revoked", False],
			["Accepted", "Rejected", False],
			["Rejected", "Forfeited", False],
			["Rejected", "Revoked", False],
			["Forfeited", "Revoked", False],
			["Revoked", "Forfeited", False],
			["Pending", "Expired", True],
			["Accepted", "Expired", False],
			["Expired", "Accepted", False],
			["Expired", "Pending", False],
		]

		support_access: SupportAccess = frappe.new_doc("Support Access")
		for status_from, status_to, expected in combinations:
			with self.subTest(status_from=status_from, status_to=status_to, expected=expected):
				is_valid = support_access.is_valid_status_transition(status_from, status_to)
				self.assertEqual(is_valid, expected)


# Support Access mails the target team on insert.
@patch("frappe.sendmail", new=Mock())
class IntegrationTestSupportAccess(IntegrationTestCase):
	"""
	Integration tests for SupportAccess.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		self.site = create_test_site(team=create_test_press_admin_team().name)

	def tearDown(self):
		frappe.db.rollback()

	def create_support_access(self, status: str = "Pending", days_old: int = 0) -> SupportAccess:
		access = frappe.get_doc(
			{
				"doctype": "Support Access",
				"requested_by": self.team.user,
				"requested_team": self.team.name,
				"reason": "Debugging",
				"status": status,
				"resources": [{"document_type": "Site", "document_name": self.site.name}],
			}
		).insert(ignore_permissions=True)
		creation = frappe.utils.add_to_date(frappe.utils.now_datetime(), days=-days_old)
		frappe.db.set_value("Support Access", access.name, "creation", creation, update_modified=False)
		return access

	def status_of(self, access: SupportAccess) -> str:
		return frappe.db.get_value("Support Access", access.name, "status")

	def test_pending_request_older_than_seven_days_is_expired(self):
		access = self.create_support_access(days_old=8)
		expire_pending_requests()
		self.assertEqual(self.status_of(access), "Expired")

	def test_pending_request_younger_than_seven_days_stays_pending(self):
		access = self.create_support_access(days_old=6)
		expire_pending_requests()
		self.assertEqual(self.status_of(access), "Pending")

	def test_old_request_that_is_not_pending_keeps_its_status(self):
		access = self.create_support_access(status="Rejected", days_old=8)
		expire_pending_requests()
		self.assertEqual(self.status_of(access), "Rejected")
