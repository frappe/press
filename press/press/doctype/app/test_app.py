# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt


import frappe
import unittest
from press.press.doctype.team.test_team import create_test_team

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from press.press.doctype.app.app import App


def create_test_app(name: str = "frappe", title: str = "Frappe Framework") -> "App":
	return frappe.get_doc({"doctype": "App", "name": name, "title": title}).insert(
		ignore_if_duplicate=True
	)


class TestApp(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_frappe_app(self):
		app = create_test_app("frappe", "Frappe Framework")
		self.assertEqual(app.frappe, True)

		source = app.add_source(
			"Version 12",
			"https://github.com/frappe/frappe",
			"version-12",
			create_test_team().name,
		)
		self.assertEqual(source.repository, "frappe")
		self.assertEqual(source.repository_owner, "frappe")

		self.assertEqual(len(source.versions), 1)
		self.assertEqual(source.versions[0].version, "Version 12")

	def test_create_non_frappe_app(self):
		app = create_test_app("erpnext", "ERPNext")
		self.assertEqual(app.frappe, False)

		source = app.add_source(
			"Version 12",
			"https://github.com/frappe/erpnext",
			"version-12",
			create_test_team().name,
		)
		self.assertEqual(source.repository, "erpnext")
		self.assertEqual(source.repository_owner, "frappe")

		self.assertEqual(len(source.versions), 1)
		self.assertEqual(source.versions[0].version, "Version 12")

	def test_create_app_with_multiple_sources(self):
		app = create_test_app("frappe", "Frappe Framework")

		source_1 = app.add_source(
			"Version 12",
			"https://github.com/frappe/frappe",
			"version-12",
			create_test_team().name,
		)
		source_2 = app.add_source(
			"Version 13",
			"https://github.com/frappe/frappe",
			"version-13",
			create_test_team().name,
		)
		self.assertEqual(source_1.branch, "version-12")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		self.assertEqual(source_2.branch, "version-13")
		self.assertEqual(len(source_2.versions), 1)
		self.assertEqual(source_2.versions[0].version, "Version 13")

	def test_create_app_with_one_source_multiple_versions(self):
		app = create_test_app("erpnext_documentation", "ERPNext Documentation")
		team_name = create_test_team().name

		source_1 = app.add_source(
			"Version 12",
			"https://github.com/frappe/erpnext_documentation",
			"master",
			team_name,
		)
		self.assertEqual(source_1.branch, "master")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		source_2 = app.add_source(
			"Version 13",
			"https://github.com/frappe/erpnext_documentation",
			"master",
			team_name,
		)

		self.assertEqual(source_1.name, source_2.name)
		self.assertEqual(len(source_2.versions), 2)
		self.assertEqual(source_2.versions[0].version, "Version 12")
		self.assertEqual(source_2.versions[1].version, "Version 13")

	def test_create_app_add_second_source_after_insert(self):
		app = create_test_app("frappe", "Frappe Framework")
		source_1 = app.add_source(
			"Version 12",
			"https://github.com/frappe/frappe",
			"version-12",
			create_test_team().name,
		)
		self.assertEqual(source_1.branch, "version-12")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		source_2 = app.add_source(
			"Version 13",
			"https://github.com/frappe/frappe",
			"version-13",
			create_test_team().name,
		)
		self.assertEqual(source_1.branch, "version-12")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		self.assertEqual(source_2.branch, "version-13")
		self.assertEqual(len(source_2.versions), 1)
		self.assertEqual(source_2.versions[0].version, "Version 13")
