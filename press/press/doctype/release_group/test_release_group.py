# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
from unittest.mock import patch

import frappe

from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app.app import new_app
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.frappe_version.test_frappe_version import (
	create_test_frappe_version,
)
from press.press.doctype.release_group.release_group import (
	ReleaseGroup,
	new_release_group,
)


def create_test_release_group(app: str) -> ReleaseGroup:
	"""
	Create Release Group doc.

	Also creates app source
	"""
	frappe_version = create_test_frappe_version()
	release_group = frappe.get_doc(
		{
			"doctype": "Release Group",
			"version": frappe_version.name,
			"enabled": True,
			"title": f"Test ReleaseGroup {frappe.mock('name')}",
		}
	)
	app_source = create_test_app_source(release_group.version, app)
	release_group.append("apps", {"app": app.name, "source": app_source.name})

	release_group.insert(ignore_if_duplicate=True)
	return release_group


@patch.object(AppSource, "create_release", create_test_app_release)
class TestReleaseGroup(unittest.TestCase):
	def setUp(self):
		for group in frappe.get_all("Deploy Candidate Difference"):
			frappe.delete_doc("Deploy Candidate Difference", group.name)
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
