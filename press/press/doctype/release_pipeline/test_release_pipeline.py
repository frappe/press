# Copyright (c) 2026, Frappe and Contributors
# See license.txt
import shutil
from unittest.mock import Mock, patch

import frappe
import tomli
from frappe.database.mariadb.database import MariaDBDatabase
from frappe.tests.utils import FrappeTestCase

from press.api.bench import deploy_and_update
from press.api.github import get_dependant_apps_with_versions
from press.exceptions import ReleasePipelineFailure
from press.press.doctype.agent_job.agent_job import poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import fake_agent_job
from press.press.doctype.app.app import parse_frappe_version
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.release_pipeline.release_pipeline import (
	ReleasePipeline,
	_resolve_dependent_app,
	_resolve_python_version_conflicts_and_update_group,
)
from press.press.doctype.server.test_server import create_test_server
from press.utils import get_current_team


def get_mock_context_file(*args, **kwargs):
	return frappe.mock("file_path")


def mock_build_monitoring(*args, **kwargs):
	"""Simulates monitoring of the build however returns success immediately without raising task enqueued error"""
	return


def mock_pre_build_validation_monitoring(*args, **kwargs):
	"""Simulates monitoring of the pre-build validation however returns success immediately without raising task enqueued error"""
	return


def mock_bench_monitoring(*args, **kwargs):
	"""Simulates monitoring of the benches however returns success immediately without raising task enqueued error"""
	return


def get_failure_pyproject_file(*args, **kwargs):
	frappe.throw("No pyproject found or something went wrong with github", frappe.ValidationError)


def get_mock_pyproject_file(*args, **kwargs):
	return tomli.loads("""[project]
		name = "helpdesk"
		authors = [
			{ name = "Frappe Technologies Pvt Ltd", email = "hello@frappe.io"}
		]
		description = "Open Source Customer Service Software"
		requires-python = ">=3.10"
		readme = "README.md"
		dynamic = ["version"]
		dependencies = [
			# Core dependencies
			"textblob==0.18.0.post0",
		]
		[build-system]
		requires = ["flit_core >=3.4,<4"]
		build-backend = "flit_core.buildapi"

		[tool.bench.frappe-dependencies]
		frappe = ">=14.0.0,<17.0.0"
		telephony = ">=0.0.1,<1.0.0"

		[tool.bench.assets]
		build_dir = "./desk"
		out_dir = "./helpdesk/public/desk"
		index_html_path = "./helpdesk/www/helpdesk/index.html"
""")


@patch.object(MariaDBDatabase, "commit", Mock())
class TestReleasePipeline(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("App")
		frappe.db.delete("App Source")
		frappe.db.delete("App Release")

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.server = create_test_server(use_for_build=True)
		cls.test_frappe_app = create_test_app("frappe")
		cls.test_erpnext_app = create_test_app("erpnext", "Erpnext App")
		cls.test_frappe_release = create_test_app_release(
			create_test_app_source(
				app=cls.test_frappe_app,
				version="Version 15",
				repository_url="https://github.com/frappe/frappe",
			),
			"79f10f8769a9a839abaef1f220da2d2eea5eea27",  # pragma: allowlist secret
		)
		cls.test_erpnext_release = create_test_app_release(
			create_test_app_source(
				app=cls.test_erpnext_app,
				version="Version 15",
				repository_url="https://github.com/frappe/erpnext",
			),
			"a2626ed55f437f69b99a29cfb0b9ead219f59458",  # pragma: allowlist secret
		)
		cls.test_release_group = create_test_release_group(
			apps=[cls.test_frappe_app, cls.test_erpnext_app],
			frappe_version="Version 15",
			servers=[cls.server.name],
		)
		frappe.db.set_single_value("Press Settings", "build_directory", "/tmp/test-build-dir/")
		frappe.db.set_single_value("Press Settings", "clone_directory", "/tmp/test-clone-dir/")
		frappe.db.set_single_value("Press Settings", "use_new_deploy_flow", 1)

	def create_deploy_and_update(self, release_group_name=None):
		deploy_and_update(
			release_group_name or self.test_release_group.name,
			apps=[
				{
					"app": "frappe",
					"source": "SRC-Frappe-001",
					"release": self.test_frappe_release.name,
					"hash": self.test_frappe_release.hash,
				},
				{
					"app": "erpnext",
					"source": "SRC-Erpnext-001",
					"release": self.test_erpnext_release.name,
					"hash": self.test_erpnext_release.hash,
				},
			],
		)

	@patch.object(DeployCandidateBuild, "build", Mock())
	@patch.object(ReleasePipeline, "monitor_build_success", mock_build_monitoring)
	def test_release_pipeline_creation(self):
		self.create_deploy_and_update()

		release_pipeline: ReleasePipeline = frappe.get_last_doc("Release Pipeline")
		self.assertEqual(release_pipeline.release_group, self.test_release_group.name)
		self.assertEqual(release_pipeline.team, get_current_team())
		workflow_doc = frappe.get_doc(
			"Press Workflow",
			{
				"linked_doctype": "Release Pipeline",
				"linked_docname": release_pipeline.name,
			},
		)
		self.assertEqual(release_pipeline.workflow, workflow_doc.name)

	@patch.object(DeployCandidateBuild, "build", Mock())
	@patch.object(ReleasePipeline, "monitor_build_success", mock_build_monitoring)
	def test_release_pipeline_build_creation(self):
		with fake_agent_job("Remote Build Job", "Success"):
			self.create_deploy_and_update()
			poll_pending_jobs()

		dcb = frappe.get_last_doc("Deploy Candidate Build")
		self.assertEqual(dcb.group, self.test_release_group.name)
		self.assertIsNotNone(dcb.deploy_candidate)

	@patch("press.api.github._get_pyproject_from_commit", get_mock_pyproject_file)
	@patch.object(DeployCandidateBuild, "build", Mock())
	@patch.object(ReleasePipeline, "monitor_build_success", mock_build_monitoring)
	def test_dynamic_apps_additions_and_bench_dependencies_upgrade(self):
		parent_hash = frappe.mock("sha1")
		frappe.db.set_single_value("Press Settings", "auto_upgrade_dependencies", 1)

		for dep in self.test_release_group.dependencies:
			if dep.dependency == "PYTHON_VERSION":
				dep.version = "3.8"
				dep.save()

		root_app = create_test_app("frappe")
		root_app_source = create_test_app_source(
			app=root_app,
			version="Version 15",
			repository_url="https://github.com/frappe/frappe",
			branch="main",
		)
		root_app_release = create_test_app_release(root_app_source, parent_hash)

		app_dependencies = get_dependant_apps_with_versions(root_app_source.name, root_app_release.hash).get(
			"frappe_dependencies"
		)
		self.assertEqual(app_dependencies, {"frappe": ">=14.0.0,<17.0.0", "telephony": ">=0.0.1,<1.0.0"})

		# Ensure system can get these!
		dependency_app = frappe.get_doc(
			{"doctype": "App", "title": "Telephony", "frappe": 1, "name": "telephony"}
		).insert()

		correct_source = create_test_app_source(
			app=dependency_app,
			version="Version 15",
			repository_url="https://github.com/frappe/dependency-app",
			branch="main",
		)

		correct_hash = frappe.mock("sha1")
		create_test_app_release(
			app_source=correct_source,
			hash=correct_hash,
		)

		self.assertNotIn(
			"telephony", [app.app for app in self.test_release_group.apps]
		)  # Ensure app was added as part of the release pipeline

		for dependency in self.test_release_group.dependencies:
			if dependency.dependency == "PYTHON_VERSION":
				self.assertEqual(dependency.version, "3.8")

		with fake_agent_job("Remote Build Job", "Success"):
			deploy_and_update(
				self.test_release_group.name,
				apps=[
					{
						"app": root_app.name,
						"source": root_app_source.name,
						"release": root_app_release.name,
						"hash": root_app_release.hash,
					}
				],
			)
			poll_pending_jobs()

		test_release_group = self.test_release_group.reload()
		self.assertIn(
			"telephony", [app.app for app in test_release_group.apps]
		)  # Ensure app was added as part of the release pipeline
		for dependency in test_release_group.dependencies:
			if dependency.dependency == "PYTHON_VERSION":
				self.assertEqual(
					dependency.version, "3.14"
				)  # >=3.10 is updated to 3.14 since we take the highest possible version that fits

		with self.assertRaises(ReleasePipelineFailure):
			_resolve_python_version_conflicts_and_update_group(
				self.test_release_group.name, {"frappe": ">=3.10", "erpnext": "<3.10"}
			)  # This should raise an error since frappe and erpnext have conflicting python version requirements

		_resolve_python_version_conflicts_and_update_group(
			self.test_release_group.name,
			{
				"frappe": ">=3.10",
				"erpnext": ">=3.10",
				"telephony": None,  # Some apps might not give their python version requirements.
			},
		)

	def test_no_failure_on_fetching_non_existent_pyproject_file(self):
		# This can happen when fetching pyproject for apps that are not part of the release but are dependencies of apps in the release
		with patch("press.api.github._get_pyproject_from_commit", get_failure_pyproject_file):
			dependent_apps = get_dependant_apps_with_versions("some_source", "some_commit", raises=False)
			self.assertEqual(dependent_apps["frappe_dependencies"], {})
			self.assertEqual(dependent_apps["python_version"], None)

		with (
			patch("press.api.github._get_pyproject_from_commit", get_failure_pyproject_file),
			self.assertRaises(frappe.ValidationError),
		):
			get_dependant_apps_with_versions("some_source", "some_commit", raises=True, cache=False)

	@patch("press.api.github._get_pyproject_from_commit", get_mock_pyproject_file)
	def test_implicit_dependency_source_addition(self):
		parent_hash = frappe.mock("sha1")

		root_app = create_test_app("someapp")
		root_app_source = create_test_app_source(
			app=root_app,
			version="Version 15",
			repository_url="https://github.com/frappe/test-app",
			branch="main",
		)
		root_app_release = create_test_app_release(root_app_source, parent_hash)

		app_dependencies = get_dependant_apps_with_versions(root_app_source.name, root_app_release.hash).get(
			"frappe_dependencies"
		)
		self.assertEqual(app_dependencies, {"frappe": ">=14.0.0,<17.0.0", "telephony": ">=0.0.1,<1.0.0"})
		supported_frappe_version = app_dependencies.pop("frappe")
		parsed_frappe_version = parse_frappe_version(
			version_string=supported_frappe_version,
			app_title="frappe",
			ease_versioning_constrains=False,
		)
		app, _ = next(iter(app_dependencies.items()))

		# No App doc yet
		with self.assertRaises(ReleasePipelineFailure):
			_resolve_dependent_app(app, parsed_frappe_version)

		dependency_app = frappe.get_doc(
			{"doctype": "App", "title": "Telephony", "frappe": 1, "name": "telephony"}
		).insert()

		# App exists, but no matching app source yet
		with self.assertRaises(ReleasePipelineFailure):
			_resolve_dependent_app(app, parsed_frappe_version)

		create_test_app_source(
			app=dependency_app,
			version="Version 15",
			repository_url="https://github.com/frappe/dependency-app",
			branch="new",
		)

		correct_source = create_test_app_source(
			app=dependency_app,
			version="Version 16",
			repository_url="https://github.com/frappe/dependency-app",
			branch="main",
		)

		correct_hash = frappe.mock("sha1")
		correct_release = create_test_app_release(
			app_source=correct_source,
			hash=correct_hash,
		)

		resolved_source, resolved_release = _resolve_dependent_app(app, parsed_frappe_version)

		self.assertEqual(resolved_source.name, correct_source.name)
		self.assertEqual(resolved_source.app, "telephony")
		self.assertEqual(resolved_release.name, correct_release.name)
		self.assertEqual(resolved_release.hash, correct_hash)

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(frappe.db.get_single_value("Press Settings", "build_directory"), ignore_errors=True)
		shutil.rmtree(frappe.db.get_single_value("Press Settings", "clone_directory"), ignore_errors=True)
