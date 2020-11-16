# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from press.press.doctype.release_group.release_group import new_release_group
from press.press.doctype.application.application import new_application


class TestReleaseGroup(unittest.TestCase):
	def setUp(self):
		for group in frappe.get_all("Release Group"):
			frappe.delete_doc("Release Group", group.name)
		for app in frappe.get_all("Application Source"):
			frappe.delete_doc("Application Source", app.name)
		for app in frappe.get_all("Application"):
			frappe.delete_doc("Application", app.name)

	def test_create_release_group(self):
		app = new_application("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)
		group = new_release_group(
			"Test Group", "Version 12", [{"app": source.application, "source": source.name}]
		)
		self.assertEqual(group.title, "Test Group")

	def test_create_release_group_set_app_from_source(self):
		app1 = new_application("frappe", "Frappe Framework")
		source1 = app1.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)
		app2 = new_application("erpnext", "ERPNext")
		source2 = app2.add_source(
			"Version 12", "https://github.com/frappe/erpnext", "version-12"
		)
		group = new_release_group(
			"Test Group", "Version 12", [{"app": source2.application, "source": source1.name}],
		)
		self.assertEqual(group.apps[0].app, source1.application)

	def test_create_release_group_fail_when_first_app_is_not_frappe(self):
		app = new_application("erpnext", "ERPNext")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/erpnext", "version-12"
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[{"app": source.application, "source": source.name}],
		)

	def test_create_release_group_fail_when_duplicate_apps(self):
		app = new_application("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[
				{"app": source.application, "source": source.name},
				{"app": source.application, "source": source.name},
			],
		)

	def test_create_release_group_fail_when_version_mismatch(self):
		app = new_application("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 13",
			[{"app": source.application, "source": source.name}],
		)

	def test_create_release_group_fail_with_duplicate_titles(self):
		app = new_application("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)
		new_release_group(
			"Test Group", "Version 12", [{"app": source.application, "source": source.name}],
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[{"app": source.application, "source": source.name}],
		)
