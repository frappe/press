from __future__ import annotations

# Copyright (c) 2026, Frappe and Contributors
# See license.txt
# import frappe
from frappe.tests import IntegrationTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES: list[str] = []  # eg. ["User"]


class IntegrationTestServerPlanType(IntegrationTestCase):
	"""
	Integration tests for ServerPlanType.
	Use this class for testing interactions between multiple components.
	"""

	pass
