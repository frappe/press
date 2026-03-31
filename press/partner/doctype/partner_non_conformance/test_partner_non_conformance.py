# Copyright (c) 2026, Frappe and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]


class UnitTestPartnerNonConformance(UnitTestCase):
	"""
	Unit tests for PartnerNonConformance.
	Use this class for testing individual functions and methods.
	"""

	pass


class IntegrationTestPartnerNonConformance(IntegrationTestCase):
	"""
	Integration tests for PartnerNonConformance.
	Use this class for testing interactions between multiple components.
	"""

	pass
