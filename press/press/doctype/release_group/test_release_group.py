# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from press.press.doctype.release_group.release_group import new_release_group
from press.press.doctype.app.app import new_app

from press.press.doctype.release_group.release_group import ReleaseGroup


def create_test_release_group(frappe_app: str) -> ReleaseGroup:
	"""Create Release Group doc."""
	name = frappe.mock("name")

	return frappe.get_doc(
		{
			"doctype": "Release Group",
			"name": f"Test Release Group{name}",
			"apps": [{"app": frappe_app}],
			"enabled": True,
		}
	).insert(ignore_if_duplicate=True)


class TestReleaseGroup(unittest.TestCase):
	def setUp(self):
		for group in frappe.get_all("Deploy"):
			frappe.delete_doc("Deploy", group.name)
		for group in frappe.get_all("Deploy Candidate"):
			frappe.delete_doc("Deploy Candidate", group.name)
		for group in frappe.get_all("Release Group"):
			frappe.delete_doc("Release Group", group.name)
		for app in frappe.get_all("App Release"):
			frappe.delete_doc("App Release", app.name)
		for app in frappe.get_all("App Source"):
			frappe.delete_doc("App Source", app.name)
		for app in frappe.get_all("App"):
			frappe.delete_doc("App", app.name)

	def test_create_release_group(self):
		app = new_app("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team="Administrator"
		)
		group = new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team="Administrator",
		)
		self.assertEqual(group.title, "Test Group")

	def test_create_release_group_set_app_from_source(self):
		app1 = new_app("frappe", "Frappe Framework")
		source1 = app1.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team="Administrator"
		)
		app2 = new_app("erpnext", "ERPNext")
		source2 = app2.add_source(
			"Version 12", "https://github.com/frappe/erpnext", "version-12", team="Administrator"
		)
		group = new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source2.app, "source": source1.name}],
			team="Administrator",
		)
		self.assertEqual(group.apps[0].app, source1.app)

	def test_create_release_group_fail_when_first_app_is_not_frappe(self):
		app = new_app("erpnext", "ERPNext")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/erpnext", "version-12", team="Administrator"
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team="Administrator",
		)

	def test_create_release_group_fail_when_duplicate_apps(self):
		app = new_app("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team="Administrator"
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[
				{"app": source.app, "source": source.name},
				{"app": source.app, "source": source.name},
			],
			team="Administrator",
		)

	def test_create_release_group_fail_when_version_mismatch(self):
		app = new_app("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team="Administrator"
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 13",
			[{"app": source.app, "source": source.name}],
			team="Administrator",
		)

	def test_create_release_group_fail_with_duplicate_titles(self):
		app = new_app("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team="Administrator"
		)
		new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team="Administrator",
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team="Administrator",
		)
