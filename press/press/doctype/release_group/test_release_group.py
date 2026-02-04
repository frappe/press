# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

import typing
from unittest.mock import Mock, patch

import frappe
from frappe.core.utils import find
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.api.bench import deploy_information
from press.api.client import get_list
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.release_group.release_group import (
	ReleaseGroup,
	new_release_group,
)
from press.press.doctype.server.server import BaseServer
from press.press.doctype.team.test_team import create_test_team

if typing.TYPE_CHECKING:
	from press.press.doctype.app.app import App


def mock_free_space(space_required: int):
	def wrapper(*args, **kwargs):
		return space_required

	return wrapper


def mock_image_size(image_size: int):
	def wrapper(*args, **kwargs):
		return {"size": image_size}

	return wrapper


def create_test_release_group(
	apps: list[App],
	user: str | None = None,
	public=False,
	frappe_version="Version 14",
	servers: list[str] | None = None,
) -> ReleaseGroup:
	"""
	Create Release Group doc.

	Also creates app source
	"""
	user = user or frappe.session.user
	release_group = frappe.get_doc(
		{
			"doctype": "Release Group",
			"version": frappe_version,
			"enabled": True,
			"title": f"Test ReleaseGroup {frappe.generate_hash(length=10)}",
			"team": frappe.get_value("Team", {"user": user}, "name"),
			"public": public,
		}
	)
	for app in apps:
		app_source = create_test_app_source(release_group.version, app)
		release_group.append("apps", {"app": app.name, "source": app_source.name})

	if servers:
		for server in servers:
			release_group.append("servers", {"server": server})

	release_group.insert(ignore_if_duplicate=True)
	release_group.reload()
	return release_group


@patch.object(AppSource, "create_release", create_test_app_release)
class TestReleaseGroup(FrappeTestCase):
	def setUp(self):
		super().setUp()

		self.team = create_test_team().name

	def tearDown(self):
		frappe.db.rollback()

	def test_create_release_group(self):
		app = create_test_app("frappe", "Frappe Framework")
		source = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/frappe",
			branch="version-12",
			team=self.team,
		)
		group = new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)
		self.assertEqual(group.title, "Test Group")

	def test_create_release_group_set_app_from_source(self):
		app1 = create_test_app("frappe", "Frappe Framework")
		source1 = app1.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/frappe",
			branch="version-12",
			team=self.team,
		)
		app2 = create_test_app("erpnext", "ERPNext")
		source2 = app2.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/erpnext",
			branch="version-12",
			team=self.team,
		)
		group = new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source2.app, "source": source1.name}],
			team=self.team,
		)
		self.assertEqual(group.apps[0].app, source1.app)

	def test_create_release_group_fail_when_first_app_is_not_frappe(self):
		app = create_test_app("erpnext", "ERPNext")
		source = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/erpnext",
			branch="version-12",
			team=self.team,
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)

	def test_create_release_group_fail_when_duplicate_apps(self):
		app = create_test_app("frappe", "Frappe Framework")
		source = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/frappe",
			branch="version-12",
			team=self.team,
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[
				{"app": source.app, "source": source.name},
				{"app": source.app, "source": source.name},
			],
			team=self.team,
		)

	def test_create_release_group_fail_when_version_mismatch(self):
		app = create_test_app("frappe", "Frappe Framework")
		source = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/frappe",
			branch="version-12",
			team=self.team,
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 13",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)

	def test_create_release_group_fail_with_duplicate_titles(self):
		app = create_test_app("frappe", "Frappe Framework")
		source = app.add_source(
			frappe_version="Version 12",
			repository_url="https://github.com/frappe/frappe",
			branch="version-12",
			team=self.team,
		)
		new_release_group(
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)
		self.assertRaises(
			frappe.ValidationError,
			new_release_group,
			"Test Group",
			"Version 12",
			[{"app": source.app, "source": source.name}],
			team=self.team,
		)

	def test_branch_change_already_on_branch(self):
		app = create_test_app()
		rg = create_test_release_group([app])
		with self.assertRaises(frappe.ValidationError):
			rg.change_app_branch("frappe", "master")

	def test_branch_change_app_source_exists(self):
		app = create_test_app()
		rg = create_test_release_group([app])

		current_app_source = frappe.get_doc("App Source", rg.apps[0].source)
		app_source = create_test_app_source(
			current_app_source.versions[0].version,
			app,
			current_app_source.repository_url,
			"develop",
		)

		rg.change_app_branch(app.name, "develop")
		rg.reload()

		# Source must be set to the available `app_source` for `app`
		self.assertEqual(rg.apps[0].source, app_source.name)

	def test_branch_change_app_source_does_not_exist(self):
		app = create_test_app()
		rg = create_test_release_group([app])
		previous_app_source = frappe.get_doc("App Source", rg.apps[0].source)

		rg.change_app_branch(app.name, "develop")
		rg.reload()

		new_app_source = frappe.get_doc("App Source", rg.apps[0].source)
		self.assertEqual(new_app_source.branch, "develop")
		self.assertEqual(new_app_source.versions[0].version, previous_app_source.versions[0].version)
		self.assertEqual(new_app_source.repository_url, previous_app_source.repository_url)
		self.assertEqual(new_app_source.app, app.name)

	def test_new_release_group_loaded_with_correct_dependencies(self):
		app = create_test_app("frappe", "Frappe Framework")
		frappe_version = frappe.get_doc("Frappe Version", "Version 14")
		group = frappe.get_doc(
			{
				"doctype": "Release Group",
				"title": "Test Group",
				"version": "Version 14",
				"apps": [{"app": app.name, "source": create_test_app_source("Version 14", app).name}],
				"team": self.team,
			}
		).insert()

		self.assertEqual(
			find(group.dependencies, lambda d: d.dependency == "PYTHON_VERSION").version,
			find(frappe_version.dependencies, lambda x: x.dependency == "PYTHON_VERSION").version,
		)

	def test_cant_set_min_greater_than_max_workers(self):
		rg = create_test_release_group([create_test_app()])
		rg.max_gunicorn_workers = 1
		rg.min_gunicorn_workers = 2
		self.assertRaises(frappe.ValidationError, rg.save)
		rg.max_background_workers = 1
		rg.min_background_workers = 2
		self.assertRaises(frappe.ValidationError, rg.save)
		rg.reload()
		try:
			rg.max_gunicorn_workers = 2
			rg.min_gunicorn_workers = 1
			rg.max_background_workers = 2
			rg.min_background_workers = 1
			rg.save()
			rg.max_gunicorn_workers = 0  # default
			rg.min_gunicorn_workers = 2
			rg.max_background_workers = 0  # default
			rg.min_background_workers = 2
			rg.save()
		except frappe.ValidationError:
			self.fail("Should not raise validation error")

	def test_update_available_shows_for_first_deploy(self):
		rg = create_test_release_group([create_test_app()])
		self.assertEqual(deploy_information(rg.name).get("update_available"), True)

	def test_fetch_environment_variables(self):
		rg = create_test_release_group([create_test_app()])
		environment_variables = [
			{"key": "test_key", "value": "test_value", "internal": False},
			{"key": "test_key_2", "value": "test_value", "internal": False},
			{"key": "secret_key", "value": "test_value", "internal": True},
		]
		for env in environment_variables:
			rg.append("environment_variables", env)
		rg.save()
		rg.reload()
		fetched_environment_variable_list = get_list(
			"Release Group Variable",
			fields=["name", "key", "value"],
			filters={"parenttype": "Release Group", "parent": rg.name},
		)
		self.assertEqual(len(fetched_environment_variable_list), 2)
		internal_environment_variables_keys = [env["key"] for env in environment_variables if env["internal"]]
		non_internal_environment_variables_keys = [
			env["key"] for env in environment_variables if not env["internal"]
		]
		for env in fetched_environment_variable_list:
			self.assertNotIn(env.key, internal_environment_variables_keys)
			self.assertIn(env.key, non_internal_environment_variables_keys)

	def test_add_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.update_environment_variable({"test_key": "test_value"})
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		self.assertEqual(rg.environment_variables[0].key, "test_key")
		self.assertEqual(rg.environment_variables[0].value, "test_value")

	def test_update_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.append("environment_variables", {"key": "test_key", "value": "test_value", "internal": 0})
		rg.save()
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		rg.update_environment_variable({"test_key": "new_test_value"})
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		self.assertEqual(rg.environment_variables[0].value, "new_test_value")

	def test_update_internal_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.append("environment_variables", {"key": "test_key", "value": "test_value", "internal": 1})
		rg.save()
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)

		def update_internal_environment_variable():
			rg.update_environment_variable({"test_key": "new_test_value"})

		self.assertRaisesRegex(
			frappe.ValidationError,
			"Environment variable test_key is internal and cannot be updated",
			update_internal_environment_variable,
		)

	def test_delete_internal_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.append("environment_variables", {"key": "test_key", "value": "test_value", "internal": 1})
		rg.save()
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		rg.delete_environment_variable("test_key")
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)

	def test_delete_environment_variable(self):
		rg = create_test_release_group([create_test_app()])
		rg.append("environment_variables", {"key": "test_key", "value": "test_value", "internal": 0})
		rg.save()
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 1)
		rg.delete_environment_variable("test_key")
		rg.reload()
		self.assertEqual(len(rg.environment_variables), 0)

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_creating_private_bench_should_not_pick_servers_used_in_restricted_site_plans(
		self,
	):
		from press.api.bench import new
		from press.press.doctype.cluster.test_cluster import create_test_cluster
		from press.press.doctype.proxy_server.test_proxy_server import (
			create_test_proxy_server,
		)
		from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
		from press.press.doctype.server.test_server import create_test_server
		from press.press.doctype.site.test_site import create_test_bench
		from press.press.doctype.site_plan.test_site_plan import create_test_plan

		cluster = create_test_cluster("Default", public=True)
		root_domain = create_test_root_domain("local.fc.frappe.dev")
		frappe.db.set_single_value("Press Settings", "domain", root_domain.name)

		frappe_app = create_test_app(name="frappe")
		new_frappe_app_source = create_test_app_source(version="Version 15", app=frappe_app)

		n1_server = create_test_proxy_server(cluster=cluster.name, domain=root_domain.name)
		f1_server = create_test_server(cluster=cluster.name, proxy_server=n1_server.name)
		f1_server.use_for_new_benches = True
		f1_server.save()
		f1_server.reload()

		n2_server = create_test_proxy_server(cluster=cluster.name, domain=root_domain.name)
		f2_server = create_test_server(cluster=cluster.name, proxy_server=n2_server.name)
		f2_server.use_for_new_benches = True
		f2_server.save()
		f2_server.reload()

		rg = create_test_release_group([frappe_app], servers=[f2_server.name])
		create_test_bench(group=rg)

		create_test_plan("Site", allowed_apps=[], release_groups=[rg.name])

		"""
		Try to create new bench, it should always pick the server which haven't used in any restricted release group
		"""
		group_name = new(
			{
				"title": "Test Bench 55",
				"apps": [{"name": frappe_app.name, "source": new_frappe_app_source.name}],
				"version": "Version 15",
				"cluster": "Default",
				"saas_app": None,
				"server": None,
			}
		)
		new_group = frappe.get_doc("Release Group", group_name)
		self.assertEqual(new_group.servers[0].server, f1_server.name)

	def test_validate_dependant_apps(self):
		release_group: ReleaseGroup = frappe.get_doc(
			{
				"doctype": "Release Group",
				"version": "Nightly",
				"enabled": True,
				"title": f"Test ReleaseGroup {frappe.mock('name')}",
				"team": self.team,
				"public": True,
			}
		)
		frappe_app = create_test_app()
		hrms_app = create_test_app(name="hrms", title="test-hrms")

		hrms_app_source = create_test_app_source(
			"Nightly", hrms_app, "https://github.com/frappe/hrms", "master", team=self.team
		)
		frappe_app_source = create_test_app_source(
			"Nightly", frappe_app, "https://github.com/frappe/frappe", "master", team=self.team
		)

		for app, app_source in [(frappe_app, frappe_app_source), (hrms_app, hrms_app_source)]:
			release_group.append("apps", {"app": app.name, "source": app_source.name})

		release_group.check_dependent_apps = True

		with self.assertRaises(frappe.exceptions.ValidationError):
			release_group.insert()

		# Insert dependant app and check if it works
		erpnext = create_test_app("erpnext", "ERPNext")
		erpnext_app_source = create_test_app_source(
			"Nightly", erpnext, "https://github.com/frappe/erpnext", "master", self.team
		)

		release_group.append("apps", {"app": erpnext.name, "source": erpnext_app_source.name})
		release_group.insert()

	@patch.object(frappe, "enqueue_doc", new=Mock())
	def test_multiple_platform_server_addition(self):
		def create_build_and_succeed(release_group: ReleaseGroup):
			deploy_candidate = release_group.create_deploy_candidate()
			response = deploy_candidate.build()
			deploy_candidate_name = response["message"]
			frappe.db.set_value("Deploy Candidate Build", deploy_candidate_name, "status", "Success")

		from press.press.doctype.cluster.test_cluster import create_test_cluster
		from press.press.doctype.proxy_server.test_proxy_server import (
			create_test_proxy_server,
		)
		from press.press.doctype.root_domain.test_root_domain import create_test_root_domain
		from press.press.doctype.server.test_server import create_test_server

		cluster = create_test_cluster("Default", public=True)
		root_domain = create_test_root_domain("local.fc.frappe.dev")
		n1_server = create_test_proxy_server(cluster=cluster.name, domain=root_domain.name)

		f1_server = create_test_server(cluster=cluster.name, proxy_server=n1_server.name, use_for_build=True)
		f2_server = create_test_server(
			cluster=cluster.name, proxy_server=n1_server.name, platform="arm64", use_for_build=True
		)

		f1_server.save()
		f2_server.save()

		rg = create_test_release_group([create_test_app()], servers=[f1_server.name])

		with self.assertRaises(frappe.ValidationError):
			# No previous builds present
			rg.add_server(f2_server.name, True)

		create_build_and_succeed(rg)

		# This server addition created a deploy candidate build
		rg.add_server(f2_server.name, True)
		arm_build = frappe.get_value("Deploy Candidate Build", {"group": rg.name, "platform": "arm64"})

		self.assertTrue(arm_build)

		# Assert added deploy candidate build has a `deploy on server` field
		self.assertEqual(
			frappe.get_value("Deploy Candidate Build", arm_build, "deploy_on_server"), f2_server.name
		)

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	@patch.object(BaseServer, "calculated_increase_disk_size", Mock())
	def test_insufficient_space(self):
		from press.press.doctype.server.test_server import create_test_server
		from press.press.doctype.site.test_site import create_test_bench

		app = create_test_app()
		server = create_test_server(auto_increase_storage=False)
		test_release_group = create_test_release_group([app], servers=[server.name])
		create_test_bench(group=test_release_group)

		with (
			patch.object(BaseServer, "free_space", mock_free_space(space_required=54000000000)),
			patch.object(Agent, "get", mock_image_size(5.21)),
		):  # Image size is 5.2gb:  # mocking 50 gib of storage enough space!
			test_release_group.check_app_server_storage()

		with (
			self.assertRaises(frappe.ValidationError),
			patch.object(BaseServer, "free_space", mock_free_space(space_required=5400000000)),
			patch.object(Agent, "get", mock_image_size(6)),
		):  # Image size is 6gb:  # mocking 5 gib of storage enough space!
			test_release_group.check_app_server_storage()

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	@patch.object(BaseServer, "calculated_increase_disk_size", Mock())
	@patch.object(Agent, "get", mock_image_size(60))
	@patch.object(BaseServer, "free_space", mock_free_space(space_required=5400000000))
	def test_insufficient_space_on_auto_add_storage_servers(self):
		from press.press.doctype.server.test_server import create_test_server
		from press.press.doctype.site.test_site import create_test_bench

		# In case of public and servers with auto increase storage
		# We should avoid throwing space errors instead just increment it for them

		app = create_test_app()
		server = create_test_server(auto_increase_storage=1)
		test_release_group = create_test_release_group([app], servers=[server.name])
		create_test_bench(group=test_release_group)

		test_release_group.check_app_server_storage()
