import json
from unittest.mock import Mock, patch

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase

from press.api.bench import deploy_information, update_dependencies
from press.patches.v0_8_0.bump_v15_bench_version_to_5_31_0 import execute
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.utils import get_current_team


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch.object(frappe.db, "commit", new=Mock())
class TestBumpV15BenchVersion(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		self.app = create_test_app()
		self.app.add_source(
			frappe_version="Version 15",
			repository_url="https://github.com/frappe/frappe",
			branch="version-15",
			team=get_current_team(),
			public=True,
		)
		create_test_server().db_set("use_for_new_benches", True)
		self.group = create_test_release_group([self.app], frappe_version="Version 15")

	def tearDown(self):
		frappe.db.rollback()

	def bench_version(self):
		self.group.reload()
		return find(self.group.dependencies, lambda d: d.dependency == "BENCH_VERSION").version

	def set_bench_version(self, version):
		dependencies = [{"key": d.dependency, "value": d.version} for d in self.group.dependencies]
		find(dependencies, lambda d: d["key"] == "BENCH_VERSION")["value"] = version
		update_dependencies(self.group.name, json.dumps(dependencies))

	def test_new_version_15_group_gets_bench_5_31_0_from_frappe_version(self):
		self.assertEqual(self.bench_version(), "5.31.0")

	def test_patch_bumps_outdated_group_to_5_31_0_and_shows_update_available(self):
		self.set_bench_version("5.27.0")
		create_test_bench(group=self.group)  # deploy, so the pending dependency update is consumed
		self.assertFalse(deploy_information(self.group.name)["update_available"])

		execute()

		self.assertEqual(self.bench_version(), "5.31.0")
		self.assertTrue(deploy_information(self.group.name)["update_available"])

	def test_patch_leaves_groups_of_other_versions_alone(self):
		self.app.add_source(
			frappe_version="Version 14",
			repository_url="https://github.com/frappe/frappe",
			branch="version-14",
			team=get_current_team(),
			public=True,
		)
		group_14 = create_test_release_group([self.app], frappe_version="Version 14")
		version_14_bench_version = find(
			group_14.dependencies, lambda d: d.dependency == "BENCH_VERSION"
		).version

		execute()

		group_14.reload()
		self.assertEqual(
			find(group_14.dependencies, lambda d: d.dependency == "BENCH_VERSION").version,
			version_14_bench_version,
		)
