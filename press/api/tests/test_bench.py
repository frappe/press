from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app


from press.api.bench import deploy, get, new, all, update_config, bench_config
from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.bench.test_bench import create_test_bench
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
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
	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock()
	)
	def test_deploy_fn_deploys_bench_container(self):
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
		DeployCandidate.command += (
			" --cache-from type=gha --cache-to type=gha,mode=max --load"
		)
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
		try:
			image = client.images.get(image_name)
		except docker.errors.ImageNotFound:
			self.fail(f"Image {image_name} not found. Found {client.images.list()}")
		self.assertIn(image_name, [tag for tag in image.tags])


class TestAPIBenchConfig(FrappeTestCase):
	def setUp(self):
		app = create_test_app()
		self.rg = create_test_release_group([app])

		self.config = [
			{"key": "max_file_size", "value": "1234", "type": "Number"},
			{"key": "mail_login", "value": "a@a.com", "type": "String"},
			{"key": "skip_setup_wizard", "value": "1", "type": "Boolean"},
			{"key": "limits", "value": '{"limit": "val"}', "type": "JSON"},
			{"key": "http_timeout", "value": 120, "type": "Number", "internal": False},
		]

		update_config(self.rg.name, self.config)
		self.rg.reload()

	def tearDown(self):
		frappe.db.rollback()

	def test_bench_config_api(self):
		configs = bench_config(self.rg.name)
		self.assertListEqual(configs, self.config)

	def test_bench_config_updation(self):
		new_bench_config = frappe.parse_json(self.rg.bench_config)

		self.assertEqual(
			frappe.parse_json(self.rg.common_site_config),
			{
				"max_file_size": 1234,
				"mail_login": "a@a.com",
				"skip_setup_wizard": True,
				"limits": {"limit": "val"},
			},
		)
		self.assertEqual(new_bench_config, {"http_timeout": 120})

	def test_bench_config_is_updated_in_subsequent_benches(self):
		bench = create_test_bench(group=self.rg)
		bench.reload()

		self.assertIn(("http_timeout", 120), frappe.parse_json(bench.bench_config).items())

		for key, value in frappe.parse_json(self.rg.common_site_config).items():
			self.assertEqual(value, frappe.parse_json(bench.config).get(key))


class TestAPIBenchList(FrappeTestCase):
	def setUp(self):
		from press.press.doctype.press_tag.test_press_tag import create_and_add_test_tag

		app = create_test_app()

		active_group = create_test_release_group([app])
		create_test_bench(group=active_group)
		self.active_bench_dict = {
			"number_of_sites": 0,
			"name": active_group.name,
			"title": active_group.title,
			"version": active_group.version,
			"creation": active_group.creation,
			"tags": [],
			"number_of_apps": 1,
			"status": "Active",
		}

		group_awaiting_deploy = create_test_release_group([app])
		self.bench_awaiting_deploy_dict = {
			"number_of_sites": 0,
			"name": group_awaiting_deploy.name,
			"title": group_awaiting_deploy.title,
			"version": group_awaiting_deploy.version,
			"creation": group_awaiting_deploy.creation,
			"tags": [],
			"number_of_apps": 1,
			"status": "Awaiting Deploy",
		}

		group_with_tag = create_test_release_group([app])
		test_tag = create_and_add_test_tag(group_with_tag.name, "Release Group")
		create_test_bench(group=group_with_tag)
		self.bench_with_tag_dict = {
			"number_of_sites": 0,
			"name": group_with_tag.name,
			"title": group_with_tag.title,
			"version": group_with_tag.version,
			"creation": group_with_tag.creation,
			"tags": [test_tag.tag],
			"number_of_apps": 1,
			"status": "Active",
		}

	def tearDown(self):
		frappe.db.rollback()

	def test_list_all_benches(self):
		self.assertCountEqual(
			all(),
			[self.active_bench_dict, self.bench_awaiting_deploy_dict, self.bench_with_tag_dict],
		)

	def test_list_active_benches(self):
		self.assertCountEqual(
			all(bench_filter="Active"), [self.active_bench_dict, self.bench_with_tag_dict]
		)

	def test_list_awaiting_deploy_benches(self):
		self.assertEqual(
			all(bench_filter="Awaiting Deploy"), [self.bench_awaiting_deploy_dict]
		)

	def test_list_tagged_benches(self):
		self.assertEqual(all(bench_filter="tag:test_tag"), [self.bench_with_tag_dict])
