import json
from unittest.mock import Mock, patch

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase

from press.api.bench import deploy_information, update_dependencies
from press.patches.v0_8_0.bump_v16_nightly_node_version_to_24_22_1 import execute
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.utils import get_current_team


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch.object(frappe.db, "commit", new=Mock())
class TestBumpV16NightlyNodeVersion(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		self.app = create_test_app()
		self.app.add_source(
			frappe_version="Version 16",
			repository_url="https://github.com/frappe/frappe",
			branch="version-16",
			team=get_current_team(),
			public=True,
		)
		create_test_server().db_set("use_for_new_benches", True)
		self.group = create_test_release_group([self.app], frappe_version="Version 16")

	def tearDown(self):
		frappe.db.rollback()

	def node_version(self):
		self.group.reload()
		return find(self.group.dependencies, lambda d: d.dependency == "NODE_VERSION").version

	def set_node_version(self, version):
		dependencies = [{"key": d.dependency, "value": d.version} for d in self.group.dependencies]
		find(dependencies, lambda d: d["key"] == "NODE_VERSION")["value"] = version
		update_dependencies(self.group.name, json.dumps(dependencies))

	def test_new_version_16_group_gets_node_24_22_1_from_frappe_version(self):
		self.assertEqual(self.node_version(), "24.22.1")

	def test_patch_bumps_older_node_24_group_to_24_22_1_and_shows_update_available(self):
		self.set_node_version("24.12.0")
		create_test_bench(group=self.group)  # deploy, so the pending dependency update is consumed
		self.assertFalse(deploy_information(self.group.name)["update_available"])

		execute()

		self.assertEqual(self.node_version(), "24.22.1")
		self.assertTrue(deploy_information(self.group.name)["update_available"])

	def test_patch_leaves_group_on_another_node_major_alone(self):
		self.set_node_version("26.0.0")

		execute()

		self.assertEqual(self.node_version(), "26.0.0")
