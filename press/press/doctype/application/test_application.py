# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from press.press.doctype.application.application import new_application


class TestApplication(unittest.TestCase):
	def test_create_frappe_application(self):
		app = new_application("frappe", "Frappe Framework")
		self.assertEqual(app.frappe, True)

		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)
		self.assertEqual(source.repository, "frappe")
		self.assertEqual(source.repository_owner, "frappe")

		self.assertEqual(len(source.versions), 1)
		self.assertEqual(source.versions[0].version, "Version 12")

	def test_create_non_frappe_application(self):
		app = new_application("erpnext", "ERPNext")
		self.assertEqual(app.frappe, False)

		source = app.add_source(
			"Version 12", "https://github.com/frappe/erpnext", "version-12"
		)
		self.assertEqual(source.repository, "erpnext")
		self.assertEqual(source.repository_owner, "frappe")

		self.assertEqual(len(source.versions), 1)
		self.assertEqual(source.versions[0].version, "Version 12")

	def test_create_app_with_multiple_sources(self):
		app = new_application("frappe", "Frappe Framework")

		source_1 = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)
		source_2 = app.add_source(
			"Version 13", "https://github.com/frappe/frappe", "version-13"
		)
		self.assertEqual(source_1.branch, "version-12")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		self.assertEqual(source_2.branch, "version-13")
		self.assertEqual(len(source_2.versions), 1)
		self.assertEqual(source_2.versions[0].version, "Version 13")

	def test_create_app_with_one_source_multiple_versions(self):
		app = new_application("erpnext_documentation", "ERPNext Documentation")

		source_1 = app.add_source(
			"Version 12", "https://github.com/frappe/erpnext_documentation", "master"
		)
		self.assertEqual(source_1.branch, "master")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		source_2 = app.add_source(
			"Version 13", "https://github.com/frappe/erpnext_documentation", "master"
		)

		self.assertEqual(source_1.name, source_2.name)
		self.assertEqual(len(source_2.versions), 2)
		self.assertEqual(source_2.versions[0].version, "Version 12")
		self.assertEqual(source_2.versions[1].version, "Version 13")

	def test_create_app_add_second_source_after_insert(self):
		app = new_application("frappe", "Frappe Framework")
		source_1 = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)
		self.assertEqual(source_1.branch, "version-12")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		source_2 = app.add_source(
			"Version 13", "https://github.com/frappe/frappe", "version-13"
		)
		self.assertEqual(source_1.branch, "version-12")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		self.assertEqual(source_2.branch, "version-13")
		self.assertEqual(len(source_2.versions), 1)
		self.assertEqual(source_2.versions[0].version, "Version 13")

	def test_create_app_with_similar_sources_failure(self):
		app = new_application("frappe", "Frappe Framework")
		source = app.add_source(
			"Version 12", "https://github.com/frappe/frappe", "version-12"
		)

		self.assertEqual(len(source.versions), 1)
		self.assertEqual(source.versions[0].version, "Version 12")

		self.assertRaises(
			frappe.ValidationError,
			app.add_source,
			"Version 12",
			"https://github.com/frappe/frappe",
			"version-12",
		)

	def setUp(self):
		for group in frappe.get_all("Deploy Candidate"):
			frappe.delete_doc("Deploy Candidate", group.name)
		for group in frappe.get_all("Release Group"):
			frappe.delete_doc("Release Group", group.name)
		for app in frappe.get_all("Application Release"):
			frappe.delete_doc("Application Release", app.name)
		for app in frappe.get_all("Application Source"):
			frappe.delete_doc("Application Source", app.name)
		for app in frappe.get_all("Application"):
			frappe.delete_doc("Application", app.name)
