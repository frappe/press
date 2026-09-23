import json

import frappe
from frappe.tests.utils import FrappeTestCase

from press.patches.v0_8_0.clean_up_render_safe_exec_config import execute
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import create_test_release_group


class TestCleanUpRenderSafeExecConfig(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def group_with_config(self, rows: list[tuple[str, str]]):
		group = create_test_release_group([create_test_app()])
		for key, value in rows:
			group.append("common_site_config_table", {"key": key, "value": value, "type": "Number"})
		group.save()
		return group

	def config_rows(self, group):
		group.reload()
		return [(row.key, row.value) for row in group.common_site_config_table]

	def test_patch_keeps_only_the_last_copy_of_a_duplicated_key(self):
		group = self.group_with_config([("render_key", "0"), ("render_key", "0"), ("render_key", "1")])
		execute()
		self.assertEqual(self.config_rows(group), [("render_key", "1")])

	def test_patch_does_not_change_the_effective_common_site_config(self):
		group = self.group_with_config([("render_key", "0"), ("max_file_size", "5"), ("render_key", "1")])
		before = json.loads(group.common_site_config)
		execute()
		group.reload()
		group.save()
		self.assertEqual(json.loads(group.common_site_config), before)

	def test_patch_removes_disable_render_safe_exec_from_the_blacklist(self):
		frappe.get_doc({"doctype": "Site Config Key Blacklist", "key": "disable_render_safe_exec"}).insert()
		execute()
		self.assertFalse(frappe.db.exists("Site Config Key Blacklist", "disable_render_safe_exec"))

	def test_patch_leaves_groups_without_duplicates_unchanged(self):
		group = self.group_with_config([("render_key", "0"), ("max_file_size", "5")])
		execute()
		self.assertEqual(self.config_rows(group), [("render_key", "0"), ("max_file_size", "5")])
