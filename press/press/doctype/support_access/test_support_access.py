# Copyright (c) 2025, Frappe and Contributors
# See license.txt

from typing import TYPE_CHECKING

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

if TYPE_CHECKING:
	from press.press.doctype.support_access.support_access import SupportAccess

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
		]

		support_access: SupportAccess = frappe.new_doc("Support Access")
		for status_from, status_to, expected in combinations:
			with self.subTest(status_from=status_from, status_to=status_to, expected=expected):
				is_valid = support_access.is_valid_status_transition(status_from, status_to)
				self.assertEqual(is_valid, expected)


class IntegrationTestSupportAccess(IntegrationTestCase):
	"""
	Integration tests for SupportAccess.
	Use this class for testing interactions between multiple components.
	"""

	pass
