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
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.release_pipeline.release_pipeline import (
	ReleasePipeline,
	_resolve_dependent_app,
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
		frappe = ">=15.40.4,<17.0.0"
		telephony = ">=15.40.0,<17.0.0"

		[tool.bench.assets]
		build_dir = "./desk"
		out_dir = "./helpdesk/public/desk"
		index_html_path = "./helpdesk/www/helpdesk/index.html"
""")


@patch.object(MariaDBDatabase, "commit", Mock())
class TestReleasePipeline(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		server = create_test_server(use_for_build=True)
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
			servers=[server.name],
		)
		frappe.db.set_single_value("Press Settings", "build_directory", "/tmp/test-build-dir/")
		frappe.db.set_single_value("Press Settings", "clone_directory", "/tmp/test-clone-dir/")

	def create_deploy_and_update(self):
		deploy_and_update(
			self.test_release_group.name,
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

	@patch.object(DeployCandidateBuild, "_upload_build_context", get_mock_context_file)
	@patch.object(DeployCandidateBuild, "_build", Mock())
	@patch.object(ReleasePipeline, "monitor_pre_build_validation", mock_pre_build_validation_monitoring)
	@patch.object(ReleasePipeline, "monitor_build_success", mock_build_monitoring)
	def test_release_pipeline_creation(self):
		self.create_deploy_and_update()

		release_pipeline: ReleasePipeline = frappe.get_last_doc("Release Pipeline")
		self.assertEqual(release_pipeline.release_group, self.test_release_group.name)
		self.assertEqual(release_pipeline.team, get_current_team())
		release_pipeline = frappe.get_doc(
			"Press Workflow",
			{
				"linked_doctype": "Release Pipeline",
				"linked_docname": release_pipeline.name,
			},
		)

		frappe.get_last_doc(
			"Press Workflow"
		)  # To ensure nothing is raised when fetching the workflow created for the release pipeline

	@patch.object(DeployCandidateBuild, "_upload_build_context", get_mock_context_file)
	@patch.object(DeployCandidateBuild, "_build", Mock())
	@patch.object(ReleasePipeline, "monitor_pre_build_validation", mock_pre_build_validation_monitoring)
	@patch.object(ReleasePipeline, "monitor_build_success", mock_build_monitoring)
	def test_release_pipeline_build_creation(self):
		with fake_agent_job("Remote Build Job", "Success"):
			self.create_deploy_and_update()
			poll_pending_jobs()

		frappe.get_last_doc(
			"Deploy Candidate Build"
		)  # Just ensure this is created without error since we are mocking the build

	@patch("press.api.github._get_pyproject_from_commit", get_mock_pyproject_file)
	def test_implicit_dependency_addition(self):
		parent_hash = frappe.mock("sha1")

		root_app = create_test_app("someapp")
		root_app_source = create_test_app_source(
			app=root_app,
			version="Version 15",
			repository_url="https://github.com/frappe/test-app",
			branch="main",
		)
		root_app_release = create_test_app_release(root_app_source, parent_hash)

		app_dependencies = get_dependant_apps_with_versions(root_app_source.name, root_app_release.hash)
		self.assertEqual(app_dependencies, {"telephony": ">=15.40.0,<17.0.0"})

		app, version = next(iter(app_dependencies.items()))

		# No App doc yet
		with self.assertRaises(ReleasePipelineFailure):
			_resolve_dependent_app(app, version)

		dependency_app = frappe.get_doc(
			{"doctype": "App", "title": "Telephony", "frappe": 1, "name": "telephony"}
		).insert()

		# App exists, but no matching app source yet
		with self.assertRaises(ReleasePipelineFailure):
			_resolve_dependent_app(app, version)

		create_test_app_source(
			app=dependency_app,
			version="Version 15",
			repository_url="https://github.com/frappe/dependency-app",
			branch="new",
		)

		# Still no matching supported source wrong version of app release
		with self.assertRaises(ReleasePipelineFailure):
			_resolve_dependent_app(app, version)

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

		resolved_source, resolved_release = _resolve_dependent_app(app, version)

		self.assertEqual(resolved_source.name, correct_source.name)
		self.assertEqual(resolved_source.app, "telephony")
		self.assertEqual(resolved_release.name, correct_release.name)
		self.assertEqual(resolved_release.hash, correct_hash)

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(frappe.db.get_single_value("Press Settings", "build_directory"), ignore_errors=True)
		shutil.rmtree(frappe.db.get_single_value("Press Settings", "clone_directory"), ignore_errors=True)
