# Copyright (c) 2026, Frappe and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]


class UnitTestPartnerAudit(UnitTestCase):
	"""
	Unit tests for PartnerAudit.
	Use this class for testing individual functions and methods.
	"""

	pass


class IntegrationTestPartnerAudit(IntegrationTestCase):
	"""
	Integration tests for PartnerAudit.
	Use this class for testing interactions between multiple components.
	"""

	pass
