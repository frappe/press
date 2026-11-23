# Copyright (c) 2024, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from press.press.doctype.site.site import Site


class TestSiteDatabaseUser(UnitTestCase):
	"""
	Unit tests for SiteDatabaseUser.
	Use this class for testing individual functions and methods.
	"""

	def test_database_name_is_fetched_without_file_usage(self):
		user = frappe.new_doc("Site Database User", site="example.frappe.cloud")
		site = frappe.new_doc("Site")
		with (
			patch.object(frappe, "get_doc", return_value=site),
			patch.object(Site, "fetch_info", return_value={"config": {"db_name": "_abc123"}}) as fetch_info,
		):
			self.assertEqual(user._get_database_name(), "_abc123")
		fetch_info.assert_called_once_with(database_only=True)
