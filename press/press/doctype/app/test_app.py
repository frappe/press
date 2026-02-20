# Copyright (c) 2019, Frappe and Contributors
# See license.txt


from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.app import parse_frappe_version
from press.press.doctype.team.test_team import create_test_team

if TYPE_CHECKING:
	from press.press.doctype.app.app import App


def create_test_app(name: str = "frappe", title: str = "Frappe Framework") -> "App":
	return frappe.get_doc({"doctype": "App", "name": name, "title": title}).insert(ignore_if_duplicate=True)


class TestApp(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_frappe_app(self):
		app = create_test_app("frappe", "Frappe Framework")
		self.assertEqual(app.frappe, True)

		source = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/frappe",
			branch="version-12",
			team=create_test_team().name,
		)
		self.assertEqual(source.repository, "frappe")
		self.assertEqual(source.repository_owner, "frappe")

		self.assertEqual(len(source.versions), 1)
		self.assertEqual(source.versions[0].version, "Version 12")

	def test_create_non_frappe_app(self):
		app = create_test_app("erpnext", "ERPNext")
		self.assertEqual(app.frappe, False)

		source = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/erpnext",
			branch="version-12",
			team=create_test_team().name,
		)
		self.assertEqual(source.repository, "erpnext")
		self.assertEqual(source.repository_owner, "frappe")

		self.assertEqual(len(source.versions), 1)
		self.assertEqual(source.versions[0].version, "Version 12")

	def test_create_app_with_multiple_sources(self):
		app = create_test_app("frappe", "Frappe Framework")

		source_1 = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/frappe",
			branch="version-12",
			team=create_test_team().name,
		)
		source_2 = app.add_source(
			frappe_version="Version 13",
			repository_url="https://github.com/frappe/frappe",
			branch="version-13",
			team=create_test_team().name,
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
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/erpnext_documentation",
			branch="master",
			team=team_name,
		)
		self.assertEqual(source_1.branch, "master")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		source_2 = app.add_source(
			frappe_version="Version 13",
			repository_url="https://github.com/frappe/erpnext_documentation",
			branch="master",
			team=team_name,
		)

		self.assertEqual(source_1.name, source_2.name)
		self.assertEqual(len(source_2.versions), 2)
		self.assertEqual(source_2.versions[0].version, "Version 12")
		self.assertEqual(source_2.versions[1].version, "Version 13")

	def test_create_app_add_second_source_after_insert(self):
		app = create_test_app("frappe", "Frappe Framework")
		source_1 = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/frappe",
			branch="version-12",
			team=create_test_team().name,
		)
		self.assertEqual(source_1.branch, "version-12")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		source_2 = app.add_source(
			frappe_version="Version 13",
			repository_url="https://github.com/frappe/frappe",
			branch="version-13",
			team=create_test_team().name,
		)
		self.assertEqual(source_1.branch, "version-12")
		self.assertEqual(len(source_1.versions), 1)
		self.assertEqual(source_1.versions[0].version, "Version 12")

		self.assertEqual(source_2.branch, "version-13")
		self.assertEqual(len(source_2.versions), 1)
		self.assertEqual(source_2.versions[0].version, "Version 13")

	def test_version_parsing(self):
		"""Test version parsing"""
		accepted_frappe_version_strings = [
			"Version 12",
			"Version 13",
			"Version 14",
			"Version 15",
			"Version 16",
			"Nightly",
		]

		for version_string in accepted_frappe_version_strings:
			parsed_version = parse_frappe_version(version_string, app_title="test-app")
			self.assertSetEqual(parsed_version, {version_string})

		accepted_custom_version_strings = [
			(">=16.0.0,<17.0.0", {"Version 16", "Nightly"}),
			(">=15.0.0,<16.0.0", {"Version 15", "Nightly"}),  # Nightly's version number is 15 for some reason
			(">=14.0.0,<15.0.0", {"Version 14"}),
			(">=13.0.0,<14.0.0", {"Version 13"}),
		]

		for accepted_custom_version_string, supported_versions in accepted_custom_version_strings:
			parsed_version = parse_frappe_version(accepted_custom_version_string, app_title="test-app")
			self.assertSetEqual(parsed_version, supported_versions)

		invalid_custom_version_strings = [
			">=16.0.0",
			"<15.0.0",
			">=14.0.0,",
			"<=13.0.0",
		]

		for invalid_custom_version_string in invalid_custom_version_strings:
			with self.assertRaises(frappe.ValidationError):
				parse_frappe_version(invalid_custom_version_string, app_title="test-app")

	def test_version_parsing_with_ease_versioning_constrains(self):
		"""Test version parsing with ease_versioning_constrains=True basically only lower bound major version compatibility check"""
		accepted_custom_version_strings = [
			(">=16.0.0,<17.0.0", {"Version 16", "Nightly"}),
			# Support stuff like alpha and dev
			(">=17.0.0-dev,<18.0.0", {"Nightly"}),
			(
				">=15.75.0-alpha,<16.0.0",
				{"Version 15", "Nightly"},
			),  # Nightly's version number is 15 for some reason
			(">=15.75.0,<16.0.0", {"Version 15", "Nightly"}),
			(">=15.55.0,<15.75.0", {"Version 15", "Nightly"}),
			(">=13.50.0,<14.0.0", {"Version 13"}),
		]

		for accepted_custom_version_string, supported_versions in accepted_custom_version_strings:
			parsed_version = parse_frappe_version(
				accepted_custom_version_string, app_title="test-app", ease_versioning_constrains=True
			)
			self.assertSetEqual(parsed_version, supported_versions)

		with self.assertRaises(frappe.ValidationError):
			parse_frappe_version(">=16.0.0", app_title="test-app", ease_versioning_constrains=True)

		with self.assertRaises(frappe.ValidationError):
			parse_frappe_version(
				">=16.0.0-dev,<15.0.0", app_title="test-app", ease_versioning_constrains=True
			)

		with self.assertRaises(frappe.ValidationError):
			parse_frappe_version(
				">=16.0.0,<15.0.0-dev", app_title="test-app", ease_versioning_constrains=True
			)

		with self.assertRaises(frappe.ValidationError):
			parse_frappe_version(">=16.0.0,<15.0.0", app_title="test-app", ease_versioning_constrains=True)

		self.assertEqual(
			parse_frappe_version(">=16.0.0,<16.0.0", app_title="test-app", ease_versioning_constrains=True),
			{"Version 16"},
		)
		# Won't match any version but won't throw error either
		self.assertEqual(
			parse_frappe_version(">=15.75.0,<15.0.0", app_title="test-app", ease_versioning_constrains=False),
			set(),
		)
