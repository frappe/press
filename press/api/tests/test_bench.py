import json
import os
import time
import requests
from unittest.mock import Mock, patch

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase, timeout
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app


from press.api.bench import (
	dependencies,
	deploy,
	deploy_and_update,
	deploy_information,
	get,
	new,
	all,
	update_config,
	bench_config,
	update_dependencies,
)
from press.press.doctype.app_release.test_app_release import create_test_app_release
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


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestAPIBench(FrappeTestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()
		self.version = "Version 15"
		self.app = create_test_app()
		self.app_source = self.app.add_source(
			self.version,
			repository_url="https://github.com/frappe/frappe",
			branch="version-15",
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

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	@patch.object(DeployCandidate, "_push_docker_image", new=Mock())
	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock()
	)
	def test_deploy_fn_deploys_bench_container(self):
		# mark frappe as approved so that the deploy can happen
		release = frappe.get_last_doc("App Release", {"source": self.app_source.name})
		release.status = "Approved"
		release.save()

		set_press_settings_for_docker_build()
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
		patch_dc_command_for_ci()
		deploy(group, [{"app": self.app.name}])
		dc_count_after = frappe.db.count("Deploy Candidate", filters={"group": group})
		d_count_after = frappe.db.count("Deploy", filters={"group": group})
		self.assertEqual(dc_count_after, dc_count_before + 1)
		self.assertEqual(d_count_after, d_count_before + 1)

		self._check_if_docker_image_was_built(group)

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	@patch.object(DeployCandidate, "deploy_to_production", new=Mock())
	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock()
	)
	def test_deploy_and_update_fn_creates_bench_update(self):
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

		bu_count_before = frappe.db.count("Bench Update", filters={"group": group})
		dc_count_before = frappe.db.count("Deploy Candidate", filters={"group": group})

		release = create_test_app_release(frappe.get_doc("App Source", self.app_source.name))
		deploy_and_update(group, [{"release": release.name}], [])

		bu_count_after = frappe.db.count("Bench Update", filters={"group": group})
		dc_count_after = frappe.db.count("Deploy Candidate", filters={"group": group})

		self.assertEqual(dc_count_after, dc_count_before + 1)
		self.assertEqual(bu_count_after, bu_count_before + 1)

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	)
	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock()
	)
	def test_deploy_and_update_fn_fails_without_release_argument(self):
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

		self.assertRaises(
			frappe.exceptions.MandatoryError,
			deploy_and_update,
			group,
			[{"app": self.app.name}],
			[],
		)

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock()
	)
	def test_deploy_fn_fails_without_apps(self):
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
		self.assertRaises(TypeError, deploy, group)

	@patch(
		"press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock()
	)
	def test_deploy_fn_fails_with_empty_apps(self):
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
		self.assertRaises(frappe.exceptions.MandatoryError, deploy, group, [])

	@timeout(20)
	def _check_if_docker_image_was_built(self, group: str):
		client = docker.from_env()
		dc = frappe.get_last_doc("Deploy Candidate")
		image_name = f"registry.local.frappe.dev/fc.dev/{group}:{dc.name}"
		try:
			image = client.images.get(image_name)
		except docker.errors.ImageNotFound:
			self.fail(f"Image {image_name} not found. Found {client.images.list()}")
		self.assertIn(image_name, [tag for tag in image.tags])

		test_port = 10501
		client.containers.run(
			image=image_name, remove=True, detach=True, ports={"8000/tcp": test_port}
		)
		while True:
			# Ensure that gunicorn at least responds. Usually we'll get 404 as there's no site installed *yet*
			try:
				response = requests.get(f"http://localhost:{test_port}")
				print("Received Response", response.text)
				if response.status_code < 500:
					break
			except IOError as e:
				print("Waitng for container to respond", str(e))
			time.sleep(0.5)


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

	def test_update_dependencies_set_dependencies_correctly(self):
		update_dependencies(
			self.rg.name,
			json.dumps(
				[
					{"key": "NODE_VERSION", "value": "16.11"},  # updated
					{"key": "NVM_VERSION", "value": "0.36.0"},
					{"key": "PYTHON_VERSION", "value": "3.6"},  # updated
					{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
					{"key": "BENCH_VERSION", "value": "5.15.2"},
				]
			),
		)
		self.assertFalse(self.rg.last_dependency_update)
		self.rg.reload()
		self.assertTrue(self.rg.last_dependency_update)
		self.assertEqual(
			find(self.rg.dependencies, lambda d: d.dependency == "NODE_VERSION").version, "16.11"
		)
		self.assertEqual(
			find(self.rg.dependencies, lambda d: d.dependency == "PYTHON_VERSION").version,
			"3.6",
		)

	def test_update_dependencies_throws_error_for_invalid_dependencies(self):
		self.assertRaisesRegex(
			Exception,
			"Invalid dependencies: asdf",
			update_dependencies,
			self.rg.name,
			json.dumps(
				[
					{"key": "NVM_VERSION", "value": "0.36.0"},
					{"key": "NODE_VERSION", "value": "16.36.0"},
					{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
					{"key": "BENCH_VERSION", "value": "5.15.2"},
					{
						"key": "asdf",
						"value": "10.9",
					},  # invalid dependency
				],
			),
		)

	def test_update_dependencies_throws_error_for_invalid_version(self):
		self.assertRaisesRegex(
			Exception,
			"Invalid version.*",
			update_dependencies,
			self.rg.name,
			json.dumps(
				[
					{"key": "NODE_VERSION", "value": "v16.11"},  # v is invalid
					{"key": "NVM_VERSION", "value": "0.36.0"},
					{"key": "PYTHON_VERSION", "value": "3.6"},
					{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
					{"key": "BENCH_VERSION", "value": "5.15.2"},
				],
			),
		)

	def test_cannot_remove_dependencies(self):
		self.assertRaisesRegex(
			Exception,
			"Need all required dependencies",
			update_dependencies,
			self.rg.name,
			json.dumps(
				[
					{"key": "NODE_VERSION", "value": "16.11"},
					{"key": "NVM_VERSION", "value": "0.36.0"},
					{"key": "PYTHON_VERSION", "value": "3.6"},
					{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
				],
			),
		)

	def test_cannot_add_additional_invalid_dependencies(self):
		self.assertRaisesRegex(
			Exception,
			"Need all required dependencies",
			update_dependencies,
			self.rg.name,
			json.dumps(
				[
					{"key": "NODE_VERSION", "value": "16.11"},
					{"key": "NVM_VERSION", "value": "0.36.0"},
					{"key": "PYTHON_VERSION", "value": "3.6"},
					{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
					{"key": "BENCH_VERSION", "value": "5.15.2"},
					{
						"key": "MARIADB_VERSION",
						"value": "10.9",
					},  # invalid dependency
				],
			),
		)

	def test_update_of_dependency_child_table_sets_last_dependency_update(self):
		self.assertFalse(self.rg.last_dependency_update)
		self.rg.append("dependencies", {"dependency": "MARIADB_VERSION", "version": "10.9"})
		self.rg.save()
		self.rg.reload()
		dependency_update_1 = self.rg.last_dependency_update
		self.assertTrue(dependency_update_1)
		update_dependencies(
			self.rg.name,
			json.dumps(
				[
					{"key": "NODE_VERSION", "value": "16.11"},
					{"key": "NVM_VERSION", "value": "0.36.0"},
					{"key": "PYTHON_VERSION", "value": "3.6"},
					{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
					{"key": "BENCH_VERSION", "value": "5.15.2"},
					{"key": "MARIADB_VERSION", "value": "10.9"},
				]
			),
		)
		self.rg.reload()
		dependency_update_2 = self.rg.last_dependency_update
		self.assertTrue(dependency_update_2)
		self.assertGreater(dependency_update_2, dependency_update_1)

	def test_deploy_information_shows_update_available_for_bench_when_apps_are_updated_after_dependency_updated_deploy(
		self,
	):
		update_dependencies(
			self.rg.name,
			json.dumps(
				[
					{"key": "NODE_VERSION", "value": "16.11"},
					{"key": "NVM_VERSION", "value": "0.36.0"},
					{"key": "PYTHON_VERSION", "value": "3.6"},
					{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
					{"key": "BENCH_VERSION", "value": "5.15.2"},
				]
			),
		)
		create_test_bench(
			group=self.rg
		)  # now update available due to dependency shouldn't be there (cuz create_test_bench created deploy candidate)
		self.assertFalse(deploy_information(self.rg.name)["update_available"])
		create_test_app_release(frappe.get_doc("App Source", self.rg.apps[0].source))
		self.assertTrue(deploy_information(self.rg.name)["update_available"])

	def test_deploy_information_shows_update_available_when_dependencies_are_updated(self):
		self.assertFalse(self.rg.last_dependency_update)
		create_test_bench(group=self.rg)  # avoid update available due to no deploys
		self.assertFalse(deploy_information(self.rg.name)["update_available"])
		update_dependencies(
			self.rg.name,
			json.dumps(
				[
					{"key": "NODE_VERSION", "value": "16.11"},
					{"key": "NVM_VERSION", "value": "0.36.0"},
					{"key": "PYTHON_VERSION", "value": "3.6"},
					{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
					{"key": "BENCH_VERSION", "value": "5.15.2"},
				]
			),
		)
		self.rg.reload()
		self.assertTrue(deploy_information(self.rg.name)["update_available"])

	def test_dependencies_lists_all_dependencies(self):
		deps = [
			{"key": "NODE_VERSION", "value": "16.11"},
			{"key": "NVM_VERSION", "value": "0.36.0"},
			{"key": "PYTHON_VERSION", "value": "3.6"},
			{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
			{"key": "BENCH_VERSION", "value": "5.15.2"},
		]
		update_dependencies(
			self.rg.name,
			json.dumps(deps),
		)
		active_dependencies = dependencies(self.rg.name)["active_dependencies"]
		self.assertListEqual(
			sorted(active_dependencies, key=lambda x: x["key"]),
			sorted(deps, key=lambda x: x["key"]),
		)

	def test_dependencies_shows_dependency_update_available_on_update_of_the_same(self):
		deps = [
			{"key": "NODE_VERSION", "value": "16.11"},
			{"key": "NVM_VERSION", "value": "0.36.0"},
			{"key": "PYTHON_VERSION", "value": "3.6"},
			{"key": "WKHTMLTOPDF_VERSION", "value": "0.12.5"},
			{"key": "BENCH_VERSION", "value": "5.15.2"},
		]
		self.assertFalse(dependencies(self.rg.name)["update_available"])
		create_test_bench(
			group=self.rg
		)  # don't show dependency update available for new deploys
		deps[0]["value"] = "16.12"
		update_dependencies(
			self.rg.name,
			json.dumps(deps),
		)
		self.assertTrue(dependencies(self.rg.name)["update_available"])

	def test_setting_limit_fields_creates_update_bench_config_job_as_such(self):
		bench = create_test_bench(group=self.rg)
		bench.memory_high = 1024
		bench.memory_max = 2048
		bench.memory_swap = 4096
		bench.vcpu = 2
		bench.save()

		job = frappe.get_last_doc(
			"Agent Job", {"job_type": "Update Bench Configuration", "bench": bench.name}
		)
		data = json.loads(job.request_data)

		self.assertEqual(data["bench_config"]["memory_high"], 1024)
		self.assertEqual(data["bench_config"]["memory_max"], 2048)
		self.assertEqual(data["bench_config"]["memory_swap"], 4096)
		self.assertEqual(data["bench_config"]["vcpu"], 2)

	def test_memory_swap_cannot_be_set_lower_than_memory_max(self):
		bench = create_test_bench(group=self.rg)
		bench.memory_high = 1024
		bench.memory_max = 2048
		bench.memory_swap = 1024
		self.assertRaises(
			frappe.exceptions.ValidationError,
			bench.save,
		)
		bench.reload()
		bench.memory_high = 1024
		bench.memory_max = 1024
		bench.memory_swap = -1
		try:
			bench.save()
		except Exception as e:
			print(e)
			self.fail("Memory swap should be allowed to be set to -1")

	def test_memory_max_cant_be_set_without_swap(self):
		bench = create_test_bench(group=self.rg)
		bench.memory_max = 2048
		self.assertRaises(
			frappe.exceptions.ValidationError,
			bench.save,
		)

	def test_memory_high_cant_be_set_higher_than_memory_max(self):
		bench = create_test_bench(group=self.rg)
		bench.memory_max = 2048
		bench.memory_high = 4096
		bench.memory_swap = 4096
		self.assertRaises(
			frappe.exceptions.ValidationError,
			bench.save,
		)

	def test_force_update_limits_creates_job_with_parameters(self):
		bench = create_test_bench(group=self.rg)
		bench.memory_high = 1024
		bench.memory_max = 2048
		bench.memory_swap = 4096
		bench.vcpu = 2
		bench.force_update_limits()
		job = frappe.get_last_doc(
			"Agent Job", {"job_type": "Force Update Bench Limits", "bench": bench.name}
		)
		job_data = json.loads(job.request_data)
		self.assertEqual(job_data["memory_high"], 1024)
		self.assertEqual(job_data["memory_max"], 2048)
		self.assertEqual(job_data["memory_swap"], 4096)
		self.assertEqual(job_data["vcpu"], 2)


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
			all(bench_filter={"status": "Active", "tag": ""}),
			[self.active_bench_dict, self.bench_with_tag_dict],
		)

	def test_list_awaiting_deploy_benches(self):
		self.assertEqual(
			all(bench_filter={"status": "Awaiting Deploy", "tag": ""}),
			[self.bench_awaiting_deploy_dict],
		)

	def test_list_tagged_benches(self):
		self.assertEqual(
			all(bench_filter={"status": "", "tag": "test_tag"}), [self.bench_with_tag_dict]
		)


def set_press_settings_for_docker_build() -> None:
	press_settings = create_test_press_settings()
	cwd = os.getcwd()
	back = os.path.join(cwd, "..")
	bench_dir = os.path.abspath(back)
	build_dir = os.path.join(bench_dir, "test_builds")
	clone_dir = os.path.join(bench_dir, "test_clones")
	press_settings.db_set("build_directory", build_dir)
	press_settings.db_set("clone_directory", clone_dir)
	press_settings.db_set("docker_registry_url", "registry.local.frappe.dev")


def patch_dc_command_for_ci():
	DeployCandidate.command = "docker buildx build"
	DeployCandidate.command += " --cache-from type=gha --cache-to type=gha,mode=max --load"
