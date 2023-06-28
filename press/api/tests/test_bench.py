from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app


from press.api.bench import deploy, get, new
from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.utils import get_current_team
from press.utils.test import foreground_enqueue_doc
import docker

import os


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestAPIBench(FrappeTestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()
		self.version = "Version 14"
		self.app = create_test_app()
		self.app_source = self.app.add_source(
			self.version,
			repository_url="https://github.com/frappe/frappe",
			branch="version-14",
			team=get_current_team(),
			public=True,
		)
		self.server = create_test_server()
		self.server.db_set("use_for_new_benches", True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_new_fn_creates_release_group_awaiting_deploy_when_called_by_press_admin_team(
		self,
	):
		frappe.set_user(self.team.user)
		name = new(
			{
				"title": "Test Bench",
				"apps": [{"name": self.app.name, "source": self.app_source.name}],
				"version": self.version,
				"cluster": "Default",
				"saas_app": None,
				"server": None,
			}
		)
		group = frappe.get_last_doc("Release Group")
		self.assertEqual(group.title, "Test Bench")
		self.assertEqual(group.name, name)
		get_res = get(group.name)
		self.assertEqual(get_res["status"], "Awaiting Deploy")
		self.assertEqual(get_res["public"], False)

	def _set_press_settings_for_docker_build(self):
		press_settings = create_test_press_settings()
		cwd = os.getcwd()
		back = os.path.join(cwd, "..")
		bench_dir = os.path.abspath(back)
		build_dir = os.path.join(bench_dir, "test_builds")
		clone_dir = os.path.join(bench_dir, "test_clones")
		press_settings.db_set("build_directory", build_dir)
		press_settings.db_set("clone_directory", clone_dir)
		press_settings.db_set("docker_registry_url", "registry.local.frappe.dev")

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	@patch.object(DeployCandidate, "_push_docker_image", new=Mock())
	def test_deploy_fn_deploys_bench(self):
		self._set_press_settings_for_docker_build()
		frappe.set_user(self.team.user)
		group = new(
			{
				"title": "Test Bench",
				"apps": [{"name": self.app.name, "source": self.app_source.name}],
				"version": self.version,
				"cluster": "Default",
				"saas_app": None,
				"server": None,
			}
		)

		dc_count_before = frappe.db.count("Deploy Candidate", filters={"group": group})
		d_count_before = frappe.db.count("Deploy", filters={"group": group})
		DeployCandidate.command = "docker buildx build"
		DeployCandidate.command += " --cache-from type=gha --cache-to type=gha,mode=max"
		deploy(group)
		dc_count_after = frappe.db.count("Deploy Candidate", filters={"group": group})
		d_count_after = frappe.db.count("Deploy", filters={"group": group})
		self.assertEqual(dc_count_after, dc_count_before + 1)
		self.assertEqual(d_count_after, d_count_before + 1)

		self._check_if_docker_image_was_built(group)

	def _check_if_docker_image_was_built(self, group: str):
		client = docker.from_env()
		dc = frappe.get_last_doc("Deploy Candidate")
		image_name = f"registry.local.frappe.dev/fc.dev/{group}:{dc.name}"
		image = client.images.get(image_name)
		self.assertIn(image_name, [tag for tag in image.tags])
