# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_release_difference.app_release_difference import is_migrate_needed
from press.press.doctype.team.test_team import create_test_team


class TestIsMigrateNeeded(FrappeTestCase):
	"""is_migrate_needed classifies changed file paths as requiring a database
	migration (bench migrate) or not.

	A wrong False skips data patches or schema changes and silently corrupts the
	database. A wrong True forces an unnecessary bench migrate on every trivial
	.py commit, adding minutes to each deploy.
	"""

	# --- files that require a migrate ---

	def test_patches_txt_requires_migrate(self):
		self.assertTrue(is_migrate_needed(["frappe/patches.txt"]))

	def test_hooks_py_requires_migrate(self):
		self.assertTrue(is_migrate_needed(["frappe/hooks.py"]))

	def test_fixtures_directory_requires_migrate(self):
		# regex: \w+/fixtures/ — one word segment before fixtures/
		self.assertTrue(is_migrate_needed(["erpnext/fixtures/user_type.json"]))

	def test_custom_directory_requires_migrate(self):
		# regex: \w+/\w+/custom/ — two word segments before custom/
		self.assertTrue(is_migrate_needed(["erpnext/accounts/custom/custom_field.json"]))

	def test_languages_json_requires_migrate(self):
		self.assertTrue(is_migrate_needed(["frappe/geo/languages.json"]))

	def test_doctype_json_requires_migrate(self):
		# Pattern \w+/\w+/\w+/(.+)/\1\.json matches <app>/<pkg>/<module>/<name>/<name>.json
		self.assertTrue(is_migrate_needed(["erpnext/erpnext/accounts/account/account.json"]))

	def test_one_migrate_file_in_mixed_batch_requires_migrate(self):
		self.assertTrue(
			is_migrate_needed(
				[
					"frappe/frappe/core/doctype/user/user.py",
					"frappe/patches.txt",
				]
			)
		)

	def test_nested_patches_path_requires_migrate(self):
		# The regex \w+/patches\.txt also matches nested paths
		self.assertTrue(is_migrate_needed(["erpnext/patches.txt"]))

	# --- files that do not require a migrate ---

	def test_python_file_no_migrate(self):
		self.assertFalse(is_migrate_needed(["frappe/frappe/core/doctype/user/user.py"]))

	def test_js_file_no_migrate(self):
		self.assertFalse(is_migrate_needed(["frappe/frappe/public/js/frappe.js"]))

	def test_empty_file_list_no_migrate(self):
		self.assertFalse(is_migrate_needed([]))

	def test_multiple_safe_py_files_no_migrate(self):
		self.assertFalse(
			is_migrate_needed(
				[
					"frappe/frappe/core/doctype/user/user.py",
					"erpnext/erpnext/accounts/account/account.py",
				]
			)
		)


class TestAppReleaseDifferenceValidate(FrappeTestCase):
	"""AppReleaseDifference.validate blocks same-release diffs.

	Creating a diff from a release to itself is meaningless — the deploy pipeline
	would see an empty diff and skip the migrate, even though the source and
	destination are the same commit (making the diff a no-op, not a skip).
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		from press.press.doctype.app_source.test_app_source import create_test_app_source

		self.team = create_test_team()
		self.app = create_test_app()
		self.source = create_test_app_source("Version 14", self.app, team=self.team.name)
		self.release = create_test_app_release(self.source)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_same_source_and_destination_release_raises(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "App Release Difference",
					"app": self.app.name,
					"source": self.source.name,
					"source_release": self.release.name,
					"destination_release": self.release.name,
				}
			).insert(ignore_permissions=True)

	def test_different_releases_do_not_raise(self):
		release2 = create_test_app_release(self.source)
		doc = frappe.get_doc(
			{
				"doctype": "App Release Difference",
				"app": self.app.name,
				"source": self.source.name,
				"source_release": self.release.name,
				"destination_release": release2.name,
			}
		).insert(ignore_permissions=True)
		self.assertIsNotNone(doc.name)
