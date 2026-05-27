# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app_release_difference.app_release_difference import (
	AppReleaseDifference,
	is_migrate_needed,
)


def _make_difference(source_release: str, destination_release: str) -> AppReleaseDifference:
	"""Insert an AppReleaseDifference with deploy_type='Pending'."""
	source_app = frappe.db.get_value("App Release", source_release, "app")
	source = frappe.db.get_value("App Release", source_release, "source")
	return frappe.get_doc(
		{
			"doctype": "App Release Difference",
			"app": source_app,
			"source": source,
			"source_release": source_release,
			"destination_release": destination_release,
			"deploy_type": "Pending",
		}
	).insert(ignore_permissions=True, ignore_links=True)


def _create_releases() -> tuple[str, str]:
	"""Return (release1_name, release2_name) from the same app source."""
	from press.press.doctype.app.test_app import create_test_app
	from press.press.doctype.app_release.test_app_release import create_test_app_release
	from press.press.doctype.app_source.test_app_source import create_test_app_source
	from press.press.doctype.team.test_team import create_test_team

	team = create_test_team()
	app = create_test_app()
	source = create_test_app_source("Version 14", app, team=team.name)
	r1 = create_test_app_release(source)
	r2 = create_test_app_release(source)
	return r1.name, r2.name


# ═════════════════════════════════════════════════════════════════
# 1. is_migrate_needed — file classification
# ═════════════════════════════════════════════════════════════════


class TestIsMigrateNeeded(FrappeTestCase):
	"""Unit tests for the is_migrate_needed() module-level function."""

	# -- files that require a migrate ----------------------------------------

	def test_patches_txt_requires_migrate(self):
		self.assertTrue(is_migrate_needed(["erpnext/patches.txt"]))

	def test_hooks_py_requires_migrate(self):
		self.assertTrue(is_migrate_needed(["frappe/hooks.py"]))

	def test_fixtures_directory_requires_migrate(self):
		self.assertTrue(is_migrate_needed(["erpnext/fixtures/some_fixture.json"]))

	def test_custom_directory_requires_migrate(self):
		self.assertTrue(is_migrate_needed(["erpnext/accounts/custom/some_file.json"]))

	def test_languages_json_requires_migrate(self):
		self.assertTrue(is_migrate_needed(["frappe/geo/languages.json"]))

	def test_doctype_json_requires_migrate(self):
		"""A DocType JSON (pattern: app/module/doctype/<name>/<name>.json) triggers migrate."""
		self.assertTrue(is_migrate_needed(["erpnext/accounts/doctype/journal_entry/journal_entry.json"]))

	def test_one_migrate_file_in_mixed_batch_requires_migrate(self):
		"""Even one migration file in a batch should trigger migrate."""
		files = [
			"erpnext/controllers/some_controller.py",
			"erpnext/patches.txt",
			"erpnext/www/index.html",
		]
		self.assertTrue(is_migrate_needed(files))

	def test_nested_patches_path_requires_migrate(self):
		"""patches.txt in a sub-path should still match."""
		self.assertTrue(is_migrate_needed(["myapp/patches.txt"]))

	# -- files that do NOT require a migrate ---------------------------------

	def test_python_file_no_migrate(self):
		self.assertFalse(is_migrate_needed(["erpnext/controllers/some_controller.py"]))

	def test_js_file_no_migrate(self):
		self.assertFalse(is_migrate_needed(["erpnext/public/js/controllers/form.js"]))

	def test_empty_file_list_no_migrate(self):
		self.assertFalse(is_migrate_needed([]))

	def test_multiple_safe_py_files_no_migrate(self):
		files = [
			"erpnext/controllers/a.py",
			"erpnext/controllers/b.py",
			"erpnext/utils.py",
		]
		self.assertFalse(is_migrate_needed(files))


# ═════════════════════════════════════════════════════════════════
# 2. AppReleaseDifference.validate — source/destination constraint
# ═════════════════════════════════════════════════════════════════


class TestAppReleaseDifferenceValidate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_same_source_and_destination_release_raises(self):
		"""validate() must throw when source_release == destination_release."""
		r1, _ = _create_releases()
		doc = frappe.new_doc("App Release Difference")
		doc.source_release = r1
		doc.destination_release = r1
		with self.assertRaises(frappe.ValidationError):
			doc.validate()

	def test_different_releases_do_not_raise(self):
		"""validate() must pass when source_release != destination_release."""
		r1, r2 = _create_releases()
		doc = frappe.new_doc("App Release Difference")
		doc.source_release = r1
		doc.destination_release = r2
		doc.validate()  # must NOT raise


# ═════════════════════════════════════════════════════════════════
# 3. AppReleaseDifference.has_branch_changed
# ═════════════════════════════════════════════════════════════════


class TestHasBranchChanged(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_different_branches_returns_true(self):
		"""has_branch_changed() must return True when source and destination come
		from different branches (different App Sources)."""
		from press.press.doctype.app.test_app import create_test_app
		from press.press.doctype.app_release.test_app_release import create_test_app_release
		from press.press.doctype.app_source.test_app_source import create_test_app_source
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		app = create_test_app()
		source_main = create_test_app_source("Version 14", app, branch="main", team=team.name)
		source_dev = create_test_app_source(
			"Version 15",
			app,
			repository_url="https://github.com/frappe/erpnext",
			branch="develop",
			team=team.name,
		)
		r1 = create_test_app_release(source_main)
		r2 = create_test_app_release(source_dev)

		doc = _make_difference(r1.name, r2.name)
		self.assertTrue(doc.has_branch_changed())

	def test_same_branch_returns_false(self):
		"""has_branch_changed() must return False when both releases share the same source."""
		r1, r2 = _create_releases()
		doc = _make_difference(r1, r2)
		self.assertFalse(doc.has_branch_changed())
