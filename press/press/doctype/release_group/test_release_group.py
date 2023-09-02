# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.core.utils import find
from press.press.doctype.app.app import App
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.release_group.release_group import (
	ReleaseGroup,
	new_release_group,
)
from press.press.doctype.team.test_team import create_test_team


def create_test_release_group(
	apps: list[App], user: str = None, public=False, frappe_version="Version 14"
) -> ReleaseGroup:
	"""
	Create Release Group doc.

	Also creates app source
	"""
	user = user or frappe.session.user
	release_group = frappe.get_doc(
		{
			"doctype": "Release Group",
			"version": frappe_version,
			"enabled": True,
			"title": f"Test ReleaseGroup {frappe.mock('name')}",
			"team": frappe.get_value("Team", {"user": user}, "name"),
			"public": public,
		}
	)
	for app in apps:
		app_source = create_test_app_source(release_group.version, app)
		release_group.append("apps", {"app": app.name, "source": app_source.name})

	release_group.insert(ignore_if_duplicate=True)
	release_group.reload()
	return release_group


@patch.object(AppSource, "create_release", create_test_app_release)
class TestReleaseGroup(unittest.TestCase):
	def setUp(self):
		self.team = create_test_team().name

	def tearDown(self):
		frappe.db.rollback()

	def test_create_release_group(self):
		app = create_test_app("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team=self.team
		)
		group = new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)
		self.assertEqual(group.title, "Test Group")

	def test_create_release_group_set_app_from_source(self):
		app1 = create_test_app("frappe", "Frappe Framework")
		source1 = app1.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team=self.team
		)
		app2 = create_test_app("erpnext", "ERPNext")
		source2 = app2.add_source(
			"Version 12", "https://github.com/frappe/erpnext", "version-12", team=self.team
		)
		group = new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source2.app, "source": source1.name}],
			team=self.team,
		)
		self.assertEqual(group.apps[0].app, source1.app)

	def test_create_release_group_fail_when_first_app_is_not_frappe(self):
		app = create_test_app("erpnext", "ERPNext")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/erpnext", "version-12", team=self.team
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)

	def test_create_release_group_fail_when_duplicate_apps(self):
		app = create_test_app("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team=self.team
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
			team=self.team,
		)

	def test_create_release_group_fail_when_version_mismatch(self):
		app = create_test_app("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team=self.team
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 13",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)

	def test_create_release_group_fail_with_duplicate_titles(self):
		app = create_test_app("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12", team=self.team
		)
		new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)

	def test_branch_change_already_on_branch(self):
		app = create_test_app()
		rg = create_test_release_group([app])
		with self.assertRaises(frappe.ValidationError):
			rg.change_app_branch("frappe", "master")

	def test_branch_change_app_source_exists(self):
		app = create_test_app()
		rg = create_test_release_group([app])

		current_app_source = frappe.get_doc("App Source", rg.apps[0].source)
		app_source = create_test_app_source(
			current_app_source.versions[0].version,
			app,
			current_app_source.repository_url,
			"develop",
		)

		rg.change_app_branch(app.name, "develop")
		rg.reload()

		# Source must be set to the available `app_source` for `app`
		self.assertEqual(rg.apps[0].source, app_source.name)

	def test_branch_change_app_source_does_not_exist(self):
		app = create_test_app()
		rg = create_test_release_group([app])
		previous_app_source = frappe.get_doc("App Source", rg.apps[0].source)

		rg.change_app_branch(app.name, "develop")
		rg.reload()

		new_app_source = frappe.get_doc("App Source", rg.apps[0].source)
		self.assertEqual(new_app_source.branch, "develop")
		self.assertEqual(
			new_app_source.versions[0].version, previous_app_source.versions[0].version
		)
		self.assertEqual(new_app_source.repository_url, previous_app_source.repository_url)
		self.assertEqual(new_app_source.app, app.name)

	def test_new_release_group_loaded_with_correct_dependencies(self):
		app = create_test_app("frappe", "Frappe Framework")
		frappe_version = frappe.get_doc("Frappe Version", "Version 14")
		group = frappe.get_doc(
			{
				"doctype": "Release Group",
				"title": "Test Group",
				"version": "Version 14",
				"apps": [
					{"app": app.name, "source": create_test_app_source("Version 14", app).name}
				],
				"team": self.team,
			}
		).insert()

		self.assertEqual(
			find(group.dependencies, lambda d: d.dependency == "PYTHON_VERSION").version,
			find(
				frappe_version.dependencies, lambda x: x.dependency == "PYTHON_VERSION"
			).version,
		)
