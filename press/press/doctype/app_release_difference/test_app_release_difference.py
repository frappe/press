# Copyright (c) 2020, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.app_release_difference.app_release_difference import (
	GITHUB_COMPARE_FILE_LIMIT,
	is_migrate_needed,
)


def frontend_files(count):
	return [f"flow/frontend/src/Component{index}.vue" for index in range(count)]


class TestAppReleaseDifference(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_frontend_only_file_list_below_github_limit_needs_no_migrate(self):
		self.assertFalse(is_migrate_needed(frontend_files(GITHUB_COMPARE_FILE_LIMIT - 1)))

	def test_file_list_at_github_limit_needs_migrate_because_it_may_be_truncated(self):
		self.assertTrue(is_migrate_needed(frontend_files(GITHUB_COMPARE_FILE_LIMIT)))

	def test_doctype_json_change_needs_migrate(self):
		files = ["frappe/studio/doctype/studio_app/studio_app.json"]
		self.assertTrue(is_migrate_needed(files))

	def test_hooks_change_needs_migrate(self):
		self.assertTrue(is_migrate_needed(["frappe/hooks.py"]))
