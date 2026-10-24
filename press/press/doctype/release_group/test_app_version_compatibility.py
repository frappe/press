# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.utils import get_current_team


@patch.object(AppSource, "create_release", new=Mock())
class TestAppVersionCompatibility(FrappeTestCase):
	"""A source with no known versions is unknown, not incompatible.

	Versions come from GitHub, so a source whose tags were not read has none.
	"""

	def setUp(self):
		super().setUp()
		create_test_press_admin_team()
		self.app = create_test_app()
		self.source = self.app.add_source(
			frappe_version="Version 15",
			repository_url="https://github.com/frappe/frappe",
			branch="version-15",
			team=get_current_team(),
			public=True,
		)
		self.group = create_test_release_group(
			[self.app], frappe_version="Version 15", app_sources=[self.source.name]
		)

	def tearDown(self):
		frappe.db.rollback()

	def set_versions(self, *versions: str):
		self.source.reload()
		self.source.set("versions", [])
		for version in versions:
			self.source.append("versions", {"version": version})
		self.source.save(ignore_permissions=True)
		self.source.reload()

	def test_source_without_known_versions_is_allowed(self):
		"""The case the fix is about: no version data means no verdict."""
		self.set_versions()

		self.group.validate_app_version(self.source.name)  # must not raise

	def test_source_with_a_matching_version_is_allowed(self):
		self.set_versions("Version 15")

		self.group.validate_app_version(self.source.name)  # must not raise

	def test_source_known_to_be_incompatible_is_still_rejected(self):
		"""The check must keep doing its job when there is evidence."""
		self.set_versions("Version 13", "Version 14")

		with self.assertRaisesRegex(
			frappe.ValidationError,
			"version-15 branch is no longer compatible with bench of Version 15",
		):
			self.group.validate_app_version(self.source.name)

	def test_incompatible_message_still_names_the_branch(self):
		self.set_versions("Version 13")

		with self.assertRaises(frappe.ValidationError) as ctx:
			self.group.validate_app_version(self.source.name)

		self.assertIn("version-15", str(ctx.exception))
		self.assertIn("Version 15", str(ctx.exception))
