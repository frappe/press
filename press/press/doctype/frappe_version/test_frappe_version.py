# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase


class TestFrappeVersion(FrappeTestCase):
	def test_create_frappe_version_with_default_dependencies(self):
		number = 99  # version with no fixtures
		frappe_version = frappe.get_doc(
			{
				"doctype": "Frappe Version",
				"name": f"Version {number}",
				"number": number,
			}
		).insert()
		self.assertEqual(len(frappe_version.dependencies), 5)
