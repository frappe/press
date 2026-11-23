# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import frappe
from frappe.model.naming import make_autoname
from frappe.tests import IntegrationTestCase, UnitTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


def create_test_bastion_server(status: str = "Active"):
	hostname = make_autoname("bastion.######")
	return frappe.get_doc(
		{
			"doctype": "Bastion Server",
			"hostname": hostname,
			"title": hostname,
			"status": status,
			"ip": frappe.mock("ipv4"),
		}
	).insert()


class UnitTestBastionServer(UnitTestCase):
	"""
	Unit tests for BastionServer.
	Use this class for testing individual functions and methods.
	"""

	pass


class IntegrationTestBastionServer(IntegrationTestCase):
	"""
	Integration tests for BastionServer.
	Use this class for testing interactions between multiple components.
	"""

	pass
