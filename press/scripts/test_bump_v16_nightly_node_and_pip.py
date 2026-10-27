import json
from unittest.mock import Mock, patch

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase

from press.api.bench import deploy_information, update_dependencies
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.scripts.bump_v16_nightly_node_and_pip import execute
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

	def version(self, dependency):
		self.group.reload()
		return find(self.group.dependencies, lambda d: d.dependency == dependency).version

	def set_versions(self, **versions):
		dependencies = [{"key": d.dependency, "value": d.version} for d in self.group.dependencies]
		for dependency, version in versions.items():
			find(dependencies, lambda d: d["key"] == dependency)["value"] = version
		update_dependencies(self.group.name, json.dumps(dependencies))

	def test_new_version_16_group_gets_node_24_22_1_and_pip_26_2_2_from_frappe_version(self):
		self.assertEqual(self.version("NODE_VERSION"), "24.22.1")
		self.assertEqual(self.version("PIP_VERSION"), "26.2.2")

	def test_patch_bumps_node_24_and_pip_25_3_group_and_shows_update_available(self):
		self.set_versions(NODE_VERSION="24.12.0", PIP_VERSION="25.3")
		create_test_bench(group=self.group)  # deploy, so the pending dependency update is consumed
		self.assertFalse(deploy_information(self.group.name)["update_available"])

		execute()

		self.assertEqual(self.version("NODE_VERSION"), "24.22.1")
		self.assertEqual(self.version("PIP_VERSION"), "26.2.2")
		self.assertTrue(deploy_information(self.group.name)["update_available"])

	def test_patch_leaves_group_on_another_node_major_and_pinned_pip_alone(self):
		self.set_versions(NODE_VERSION="26.0.0", PIP_VERSION="25.2")

		execute()

		self.assertEqual(self.version("NODE_VERSION"), "26.0.0")
		self.assertEqual(self.version("PIP_VERSION"), "25.2")

	def test_patch_does_not_downgrade_newer_node_24_pin(self):
		self.set_versions(NODE_VERSION="24.23.0")

		execute()

		self.assertEqual(self.version("NODE_VERSION"), "24.23.0")
