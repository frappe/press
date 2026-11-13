# Copyright (c) 2024, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


def new_banner(help_url: str):
	return frappe.get_doc(
		{"doctype": "Dashboard Banner", "title": "Maintenance", "is_global": 1, "help_url": help_url}
	)


class TestDashboardBanner(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_help_url_with_a_script_scheme_is_refused(self):
		for help_url in (
			"javascript:alert(document.cookie)",
			"javascript://docs.frappe.io/%0aalert(1)",
			"data:text/html,x",
		):
			with self.subTest(help_url=help_url), self.assertRaisesRegex(frappe.ValidationError, "Help URL"):
				new_banner(help_url).insert()

	def test_help_url_with_a_web_scheme_is_saved(self):
		banner = new_banner("https://docs.frappe.io/cloud").insert()
		self.assertEqual(banner.help_url, "https://docs.frappe.io/cloud")
