# Copyright (c) 2025, Frappe and Contributors
# See license.txt


import typing
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.bench.bench import Bench, process_bench_queue
from press.press.doctype.deploy_candidate.test_deploy_candidate import (
	create_test_deploy_candidate,
	create_test_deploy_candidate_build,
	create_test_press_admin_team,
)
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
from press.press.doctype.release_group.test_release_group import (
	create_test_release_group,
)
from press.press.doctype.server.test_server import create_test_server

if typing.TYPE_CHECKING:
	from press.press.doctype.deploy.deploy import Deploy
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate


@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestDeployCandidateBuild(FrappeTestCase):
	def setUp(self):
		super().setUp()

		self.team = create_test_press_admin_team()
		self.user: str = self.team.user
		app = create_test_app()
		self.create_build_servers()
		group = create_test_release_group([app], self.user)
		group.db_set("team", self.team.name)
		frappe.db.set_single_value("Press Settings", "docker_registry_url", "registry.digitalocean.com")
		frappe.set_user(self.user)
		self.deploy_candidate = create_test_deploy_candidate(group)
		self.deploy_candidate_build = create_test_deploy_candidate_build(self.deploy_candidate)

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def create_build_servers(self):
		self.x86_build_server = create_test_server(platform="x86_64", use_for_build=True)
		self.arm_build_server = create_test_server(platform="arm64", use_for_build=True)

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc", new=Mock())
	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock())
	@patch.object(DeployCandidateBuild, "_process_run_build", new=Mock())
	@patch.object(Bench, "after_insert", new=Mock())
	def test_correct_build_flow(self, mock_enqueue):
		import json

		app = create_test_app()

		group = create_test_release_group(
			[app], servers=[self.x86_build_server.name, self.arm_build_server.name]
		)

		dc: DeployCandidate = group.create_deploy_candidate()
		deploy_candidate_build_name = dc.build().get("message")

		deploy_candidate_build: DeployCandidateBuild = frappe.get_doc(
			"Deploy Candidate Build", deploy_candidate_build_name
		)

		deploy_candidate_build.set_build_server()
		build_server_platform = frappe.get_value("Server", deploy_candidate_build.build_server, "platform")
		self.assertEqual(build_server_platform, "x86_64")
		deploy_candidate_build.status = "Success"
		deploy_candidate_build.save()

		job = frappe._dict(
			{"request_data": json.dumps({"deploy_candidate_build": deploy_candidate_build_name})}
		)
		deploy_candidate_build.process_run_build(job, response_data=None)

		# Intel build has finished and been processed
		dc: DeployCandidate = dc.reload()
		self.assertEqual(dc.intel_build, deploy_candidate_build_name)

		# Auto triggered from process run build of the last dc
		newly_created_build: DeployCandidateBuild = frappe.get_last_doc(
			"Deploy Candidate Build", {"deploy_candidate": dc.name}
		)
		self.assertEqual(newly_created_build.platform, "arm64")

		job = frappe._dict({"request_data": json.dumps({"deploy_candidate_build": newly_created_build.name})})
		newly_created_build.status = "Success"
		newly_created_build.save()
		newly_created_build.process_run_build(job, response_data=None)

		# ARM Build has finished and been processed
		dc: DeployCandidate = dc.reload()
		self.assertEqual(dc.arm_build, newly_created_build.name)

		# Assert no more builds are created
		test_build: DeployCandidateBuild = frappe.get_last_doc(
			"Deploy Candidate Build", {"deploy_candidate": dc.name}
		)
		self.assertEqual(test_build.name, newly_created_build.name)

	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.enqueue_doc", new=Mock())
	@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit", new=Mock())
	@patch.object(Bench, "after_insert", new=Mock())
	@patch.object(DeployCandidateBuild, "_process_run_build", new=Mock())
	def test_multi_server_deploy(self, mock_enqueue):
		import json

		app = create_test_app()

		group = create_test_release_group(
			[app], servers=[self.x86_build_server.name, self.arm_build_server.name]
		)

		dc: DeployCandidate = group.create_deploy_candidate()
		deploy_candidate_build_name = dc.build_and_deploy()

		# Intel Build
		deploy_candidate_build: DeployCandidateBuild = frappe.get_doc(
			"Deploy Candidate Build", deploy_candidate_build_name
		)
		deploy_candidate_build.status = "Success"
		deploy_candidate_build.docker_image = "testdockerimage"
		deploy_candidate_build.save()
		job = frappe._dict(
			{
				"request_data": json.dumps(
					{
						"deploy_candidate_build": deploy_candidate_build_name,
						"deploy_after_build": deploy_candidate_build.deploy_after_build,
					}
				)
			}
		)
		deploy_candidate_build.process_run_build(job, response_data=None)

		# Ensure no deploy create after only one build is completed
		self.assertEqual(frappe.get_all("Deploy", {"candidate": dc.name}), [])

		# ARM Build
		newly_created_build: DeployCandidateBuild = frappe.get_last_doc(
			"Deploy Candidate Build", {"deploy_candidate": dc.name}
		)
		newly_created_build.status = "Success"
		newly_created_build.docker_image = "testdockerimage2"
		newly_created_build.save()
		job = frappe._dict(
			{
				"request_data": json.dumps(
					{
						"deploy_candidate_build": newly_created_build.name,
						"deploy_after_build": newly_created_build.deploy_after_build,
					}
				)
			}
		)
		newly_created_build.process_run_build(job, response_data=None)
		self.assertEqual(len(frappe.get_all("Deploy", {"candidate": dc.name})), 1)

		process_bench_queue()  # Ensure bench ref exists

		# Check correct build association with the bench
		deploy: Deploy = frappe.get_doc("Deploy", {"candidate": dc.name})
		for bench_ref in deploy.benches:
			server, bench_queue = bench_ref.server, bench_ref.bench
			bench = frappe.db.get_value("New Bench Queue", bench_queue, "bench")
			build = frappe.get_value("Bench", bench, "build")
			server_platform = frappe.get_value("Server", server, "platform")
			build_platform = frappe.get_value("Deploy Candidate Build", build, "platform")

			self.assertEqual(server_platform, build_platform)
			if build_platform == "arm64":
				self.assertEqual(newly_created_build.name, build)
			else:
				self.assertEqual(deploy_candidate_build.name, build)

	# -----------------------------------------------------------------------
	# Task 5: Build Pipeline unit tests
	# -----------------------------------------------------------------------

	def test_encode_dockerfile_produces_valid_base64(self, _mock_enqueue):
		"""encode_dockerfile should base64-encode the Dockerfile content so the
		agent can transport it as plain text."""
		import base64

		content = "FROM ubuntu:22.04\nRUN echo hello"
		encoded = self.deploy_candidate_build.encode_dockerfile(content)
		decoded = base64.b64decode(encoded).decode("utf-8")
		self.assertEqual(decoded, content)

	def test_encode_dockerfile_round_trips_unicode(self, _mock_enqueue):
		"""Unicode characters in the Dockerfile must survive the encode/decode
		round-trip unmodified."""
		import base64

		content = "# unicode: café résumé naïve\nRUN echo done"
		encoded = self.deploy_candidate_build.encode_dockerfile(content)
		decoded = base64.b64decode(encoded).decode("utf-8")
		self.assertEqual(decoded, content)

	def test_get_dockerfile_checkpoints_extracts_stage_slugs(self, _mock_enqueue):
		"""_get_dockerfile_checkpoints should return every slug that follows the
		'`#stage-<slug>`' pattern in the Dockerfile."""
		dockerfile = (
			"FROM ubuntu\n"
			"# `#stage-pre-essentials`\n"
			"RUN apt-get install python3\n"
			"# `#stage-apps-erpnext`\n"
			"RUN bench get-app erpnext\n"
		)
		checkpoints = self.deploy_candidate_build._get_dockerfile_checkpoints(dockerfile)
		self.assertIn("pre-essentials", checkpoints)
		self.assertIn("apps-erpnext", checkpoints)

	def test_get_dockerfile_checkpoints_returns_empty_for_no_markers(self, _mock_enqueue):
		"""When the Dockerfile has no stage markers the result should be an
		empty list — not None or an error."""
		dockerfile = "FROM ubuntu\nRUN echo hello\n"
		checkpoints = self.deploy_candidate_build._get_dockerfile_checkpoints(dockerfile)
		self.assertEqual(checkpoints, [])

	def test_check_distutils_support_python_3_12(self, _mock_enqueue):
		"""Python 3.12 dropped distutils; check_distutils_support must return
		False so the Dockerfile removes it (DISTUTILS_SUPPORTED_VERSION = <3.12)."""
		result = self.deploy_candidate_build.check_distutils_support("3.12.0")
		self.assertFalse(result)

	def test_check_distutils_support_python_3_11(self, _mock_enqueue):
		"""Python 3.11 still ships distutils (< 3.12); check_distutils_support
		must return True."""
		result = self.deploy_candidate_build.check_distutils_support("3.11.0")
		self.assertTrue(result)

	def test_check_distutils_support_python_3_9(self, _mock_enqueue):
		"""Python 3.9 still ships distutils; check_distutils_support must return
		True."""
		result = self.deploy_candidate_build.check_distutils_support("3.9.0")
		self.assertTrue(result)

	@patch.object(DeployCandidateBuild, "save", new=Mock())
	def test_add_pre_build_steps_creates_clone_step_for_each_app(self, _mock_enqueue):
		"""add_pre_build_steps should add at least one 'clone' step per app in
		the deploy candidate."""
		build = self.deploy_candidate_build
		build.build_steps = []
		build.add_pre_build_steps()
		clone_steps = [s for s in build.build_steps if s.stage_slug == "clone"]
		app_names = {app.app for app in build.candidate.apps}
		clone_app_names = {s.step_slug for s in clone_steps}
		self.assertTrue(app_names.issubset(clone_app_names))
