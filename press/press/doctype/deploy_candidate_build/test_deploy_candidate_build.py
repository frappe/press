# Copyright (c) 2025, Frappe and Contributors
# See license.txt


import json
import typing
from datetime import datetime, timedelta
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
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import (
	DeployCandidateBuild,
	Status,
	can_retry_build,
	get_build_stage_and_step,
	get_remote_step_output,
	should_build_retry_build_output,
	should_build_retry_exc,
	should_build_retry_job,
)
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


class TestShouldBuildRetryBuildOutput(FrappeTestCase):
	"""Tests for should_build_retry_build_output - pure string-matching function."""

	def test_apt_lock_triggers_retry(self):
		self.assertTrue(should_build_retry_build_output("Could not get lock /var/cache/apt/archives/lock"))

	def test_docker_cache_key_triggers_retry(self):
		self.assertTrue(
			should_build_retry_build_output(
				"failed to compute cache key: failed to calculate checksum of ref /some/path"
			)
		)

	def test_pypi_timeout_triggers_retry(self):
		self.assertTrue(
			should_build_retry_build_output("Connection to pypi.org timed out. (connect timeout=15)")
		)

	def test_gpg_key_timeout_triggers_retry(self):
		self.assertTrue(
			should_build_retry_build_output("Error: retrieving gpg key timed out.\nFailed to add key.")
		)

	def test_yarn_bad_gateway_triggers_retry(self):
		self.assertTrue(
			should_build_retry_build_output(
				'error https://registry.yarnpkg.com/some-package\nRequest failed "502 Bad Gateway"'
			)
		)

	def test_npm_internal_server_error_triggers_retry(self):
		self.assertTrue(
			should_build_retry_build_output(
				'Error: https://registry.npmjs.org/some-pkg\nRequest failed "500 Internal Server Error"'
			)
		)

	def test_yarn_bad_gateway_requires_both_strings(self):
		# Only the URL string without the status line should NOT trigger retry
		self.assertFalse(should_build_retry_build_output("error https://registry.yarnpkg.com/some-package"))

	def test_unrelated_error_does_not_trigger_retry(self):
		self.assertFalse(should_build_retry_build_output("ImportError: No module named 'some_module'"))

	def test_empty_output_does_not_trigger_retry(self):
		self.assertFalse(should_build_retry_build_output(""))


class TestShouldBuildRetryExc(FrappeTestCase):
	"""Tests for should_build_retry_exc - error string matching via exc.args."""

	def test_upload_context_failure_triggers_retry(self):
		exc = Exception("Failed to upload build context to remote docker builder")
		self.assertTrue(should_build_retry_exc(exc))

	def test_redis_connection_error_triggers_retry(self):
		exc = Exception("redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379")
		self.assertTrue(should_build_retry_exc(exc))

	def test_rq_timeout_triggers_retry(self):
		exc = Exception("rq.timeouts.JobTimeoutException: Task exceeded maximum timeout value (3600 sec)")
		self.assertTrue(should_build_retry_exc(exc))

	def test_unrelated_exception_does_not_trigger_retry(self):
		exc = Exception("KeyError: 'missing_key'")
		self.assertFalse(should_build_retry_exc(exc))

	def test_exception_with_no_args_does_not_trigger_retry(self):
		exc = Exception()
		self.assertFalse(should_build_retry_exc(exc))


class TestShouldBuildRetryJob(FrappeTestCase):
	"""Tests for should_build_retry_job - traceback string matching."""

	def _make_job(self, traceback: str | None) -> Mock:
		job = Mock()
		job.traceback = traceback
		return job

	def test_no_traceback_returns_false(self):
		self.assertFalse(should_build_retry_job(self._make_job(None)))

	def test_empty_traceback_returns_false(self):
		self.assertFalse(should_build_retry_job(self._make_job("")))

	def test_timeout_error_triggers_retry(self):
		self.assertTrue(
			should_build_retry_job(self._make_job("TimeoutError: timed out waiting for response"))
		)

	def test_connection_reset_triggers_retry(self):
		self.assertTrue(
			should_build_retry_job(
				self._make_job("ConnectionResetError: [Errno 104] Connection reset by peer")
			)
		)

	def test_connection_refused_triggers_retry(self):
		self.assertTrue(
			should_build_retry_job(self._make_job("ConnectionRefusedError: [Errno 111] Connection refused"))
		)

	def test_unrelated_traceback_does_not_trigger_retry(self):
		self.assertFalse(should_build_retry_job(self._make_job("KeyError: 'missing_key'")))


class TestGetBuildStageAndStep(FrappeTestCase):
	"""Tests for get_build_stage_and_step - pure mapping function."""

	def test_known_stage_and_step_are_mapped(self):
		stage, step = get_build_stage_and_step("pre", "essentials")
		self.assertEqual(stage, "Setup Prerequisites")
		self.assertEqual(step, "Install Essential Packages")

	def test_upload_image_step_is_mapped(self):
		stage, step = get_build_stage_and_step("upload", "image")
		self.assertEqual(stage, "Upload")
		self.assertEqual(step, "Docker Image")

	def test_clone_stage_uses_app_titles(self):
		app_titles = {"frappe": "Frappe Framework"}
		stage, step = get_build_stage_and_step("clone", "frappe", app_titles)
		self.assertEqual(stage, "Clone Repositories")
		self.assertEqual(step, "Frappe Framework")

	def test_apps_stage_uses_app_titles(self):
		app_titles = {"erpnext": "ERPNext"}
		stage, step = get_build_stage_and_step("apps", "erpnext", app_titles)
		self.assertEqual(stage, "Install Apps")
		self.assertEqual(step, "ERPNext")

	def test_clone_without_app_titles_returns_step_slug(self):
		stage, step = get_build_stage_and_step("clone", "frappe", None)
		self.assertEqual(stage, "Clone Repositories")
		self.assertEqual(step, "frappe")

	def test_unknown_stage_and_step_return_slugs_unchanged(self):
		stage, step = get_build_stage_and_step("custom_stage", "custom_step")
		self.assertEqual(stage, "custom_stage")
		self.assertEqual(step, "custom_step")


class TestGetRemoteStepOutput(FrappeTestCase):
	"""Tests for get_remote_step_output - pure dict-traversal function."""

	def test_returns_from_output_data_when_present(self):
		result = get_remote_step_output("build", {"build": ["line1", "line2"]}, None)
		self.assertEqual(result, ["line1", "line2"])

	def test_returns_none_when_response_data_is_none(self):
		self.assertIsNone(get_remote_step_output("build", {}, None))

	def test_returns_none_when_response_data_is_not_dict(self):
		self.assertIsNone(get_remote_step_output("build", {}, "invalid"))

	def test_extracts_build_output_from_response_data_steps(self):
		response_data = {
			"steps": [
				{
					"name": "Build Image",
					"commands": [{"output": json.dumps({"build": ["step1", "step2"]})}],
				}
			]
		}
		result = get_remote_step_output("build", {}, response_data)
		self.assertEqual(result, ["step1", "step2"])

	def test_extracts_push_output_from_response_data_steps(self):
		response_data = {
			"steps": [
				{
					"name": "Push Docker Image",
					"commands": [{"output": json.dumps({"push": ["pushed"]})}],
				}
			]
		}
		result = get_remote_step_output("push", {}, response_data)
		self.assertEqual(result, ["pushed"])

	def test_returns_none_when_step_name_does_not_match(self):
		response_data = {
			"steps": [
				{
					"name": "Some Other Step",
					"commands": [{"output": json.dumps({"build": ["step1"]})}],
				}
			]
		}
		self.assertIsNone(get_remote_step_output("build", {}, response_data))


class TestStatusEnum(FrappeTestCase):
	"""Tests for Status enum class methods."""

	def test_terminal_contains_failure_and_success(self):
		terminal = Status.terminal()
		self.assertIn("Failure", terminal)
		self.assertIn("Success", terminal)
		self.assertNotIn("Running", terminal)
		self.assertNotIn("Pending", terminal)

	def test_intermediate_contains_active_statuses(self):
		intermediate = Status.intermediate()
		self.assertIn("Pending", intermediate)
		self.assertIn("Running", intermediate)
		self.assertIn("Preparing", intermediate)
		self.assertNotIn("Success", intermediate)
		self.assertNotIn("Failure", intermediate)


class TestVersionCutoffs(FrappeTestCase):
	"""Documents the Python version boundaries that control Dockerfile flags.

	These two cutoffs drive which packages and pip installer are written into
	every Dockerfile we generate; a silent regression here would produce broken
	images for the affected Python version.

	We test the module constants directly — going through the class methods would
	require a real or properly-configured instance just to call semantic_version,
	which adds noise without adding coverage of anything meaningful.
	"""

	def test_distutils_cutoff_is_at_312(self):
		import semantic_version

		from press.press.doctype.deploy_candidate_build.deploy_candidate_build import (
			DISTUTILS_SUPPORTED_VERSION,
		)

		# 3.11 keeps distutils; 3.12 removes it
		self.assertIn(semantic_version.Version("3.11.0"), DISTUTILS_SUPPORTED_VERSION)
		self.assertNotIn(semantic_version.Version("3.12.0"), DISTUTILS_SUPPORTED_VERSION)

	def test_get_pip_url_range_is_32_to_38_inclusive(self):
		import semantic_version

		from press.press.doctype.deploy_candidate_build.deploy_candidate_build import (
			GET_PIP_VERSION_MODIFIED_URL,
		)

		# 3.2-3.8 uses the versioned get-pip URL; outside that range uses the default
		self.assertIn(semantic_version.Version("3.2.0"), GET_PIP_VERSION_MODIFIED_URL)
		self.assertIn(semantic_version.Version("3.8.0"), GET_PIP_VERSION_MODIFIED_URL)
		self.assertNotIn(semantic_version.Version("3.9.0"), GET_PIP_VERSION_MODIFIED_URL)
		self.assertNotIn(semantic_version.Version("3.1.0"), GET_PIP_VERSION_MODIFIED_URL)


class TestGetDockerfileCheckpoints(FrappeTestCase):
	"""Tests for _get_dockerfile_checkpoints - regex parsing, no DB needed."""

	def setUp(self):
		super().setUp()
		self.build = Mock(spec=DeployCandidateBuild)

	def test_extracts_checkpoints_from_dockerfile(self):
		dockerfile = "RUN echo `#stage-pre-essentials`\nRUN echo `#stage-apps-frappe`"
		checkpoints = DeployCandidateBuild._get_dockerfile_checkpoints(self.build, dockerfile)
		self.assertIn("pre-essentials", checkpoints)
		self.assertIn("apps-frappe", checkpoints)

	def test_returns_empty_list_when_no_checkpoints(self):
		dockerfile = "FROM ubuntu:20.04\nRUN apt-get update"
		checkpoints = DeployCandidateBuild._get_dockerfile_checkpoints(self.build, dockerfile)
		self.assertEqual(checkpoints, [])

	def test_handles_multiple_checkpoints_on_same_line(self):
		dockerfile = "RUN echo `#stage-clone-frappe` `#stage-clone-erpnext`"
		checkpoints = DeployCandidateBuild._get_dockerfile_checkpoints(self.build, dockerfile)
		self.assertIn("clone-frappe", checkpoints)
		self.assertIn("clone-erpnext", checkpoints)


class TestFailLastRunningStep(FrappeTestCase):
	"""Tests for _fail_last_running_step - list traversal, no DB needed."""

	@staticmethod
	def _make_step(status: str) -> Mock:
		step = Mock()
		step.status = status
		return step

	def test_marks_first_running_step_as_failure(self):
		build = Mock(spec=DeployCandidateBuild)
		build.build_steps = [
			self._make_step("Success"),
			self._make_step("Running"),
			self._make_step("Pending"),
		]
		DeployCandidateBuild._fail_last_running_step(build)
		self.assertEqual(build.build_steps[1].status, "Failure")
		# Steps after the running step are untouched
		self.assertEqual(build.build_steps[2].status, "Pending")

	def test_returns_early_when_failure_step_already_exists(self):
		build = Mock(spec=DeployCandidateBuild)
		build.build_steps = [
			self._make_step("Failure"),
			self._make_step("Running"),
		]
		DeployCandidateBuild._fail_last_running_step(build)
		# Running step must NOT be changed because an earlier Failure already exists
		self.assertEqual(build.build_steps[1].status, "Running")

	def test_does_nothing_when_no_running_step_exists(self):
		build = Mock(spec=DeployCandidateBuild)
		build.build_steps = [self._make_step("Success"), self._make_step("Pending")]
		DeployCandidateBuild._fail_last_running_step(build)
		self.assertEqual(build.build_steps[0].status, "Success")
		self.assertEqual(build.build_steps[1].status, "Pending")


class TestHasRemoteBuildFailed(FrappeTestCase):
	"""Tests for has_remote_build_failed - flag-checking logic, no DB needed."""

	@staticmethod
	def _make_build(has_failure_step: bool = False) -> Mock:
		build = Mock(spec=DeployCandidateBuild)
		build.upload_step_updater = None  # no upload step by default
		if has_failure_step:
			step = Mock()
			step.status = "Failure"
			build.get_first_step.return_value = step
		else:
			build.get_first_step.return_value = None
		return build

	def test_returns_true_when_job_status_is_failure(self):
		build = self._make_build()
		job = Mock(status="Failure")
		self.assertTrue(DeployCandidateBuild.has_remote_build_failed(build, job, {}))

	def test_returns_true_when_job_data_signals_build_failed(self):
		build = self._make_build()
		job = Mock(status="Success")
		self.assertTrue(DeployCandidateBuild.has_remote_build_failed(build, job, {"build_failed": True}))

	def test_returns_true_when_failure_step_exists(self):
		build = self._make_build(has_failure_step=True)
		job = Mock(status="Success")
		self.assertTrue(DeployCandidateBuild.has_remote_build_failed(build, job, {}))

	def test_returns_false_when_no_failure_conditions(self):
		build = self._make_build()
		job = Mock(status="Success")
		self.assertFalse(DeployCandidateBuild.has_remote_build_failed(build, job, {}))


class TestShouldBuildRetryMethod(FrappeTestCase):
	"""Tests for DeployCandidateBuild.should_build_retry - combines pure helpers."""

	@staticmethod
	def _make_build(status: str = "Failure", retry_count: int = 0, build_output: str = "") -> Mock:
		build = Mock(spec=DeployCandidateBuild)
		build.status = status
		build.retry_count = retry_count
		build.build_output = build_output
		return build

	def test_returns_false_when_status_is_not_failure(self):
		build = self._make_build(status="Running")
		self.assertFalse(DeployCandidateBuild.should_build_retry(build, None, None))

	def test_returns_false_when_retry_count_is_3(self):
		build = self._make_build(retry_count=3)
		self.assertFalse(DeployCandidateBuild.should_build_retry(build, None, None))

	def test_returns_true_for_retriable_build_output(self):
		build = self._make_build(build_output="Could not get lock /var/cache/apt/archives/lock")
		self.assertTrue(DeployCandidateBuild.should_build_retry(build, None, None))

	def test_returns_true_for_retriable_exception(self):
		build = self._make_build()
		exc = Exception("Failed to upload build context to remote docker builder")
		self.assertTrue(DeployCandidateBuild.should_build_retry(build, exc, None))

	def test_returns_true_for_retriable_job_traceback(self):
		build = self._make_build()
		job = Mock()
		job.traceback = "TimeoutError: timed out"
		self.assertTrue(DeployCandidateBuild.should_build_retry(build, None, job))

	def test_returns_false_when_no_retry_conditions_met(self):
		build = self._make_build(build_output="ImportError: missing module")
		self.assertFalse(DeployCandidateBuild.should_build_retry(build, None, None))


class TestGetFirstStep(FrappeTestCase):
	"""Tests for get_first_step - list traversal, no DB needed."""

	@staticmethod
	def _make_step(**kwargs) -> Mock:
		step = Mock()
		step.get = lambda key: kwargs.get(key)
		return step

	def test_returns_first_step_matching_string_value(self):
		build = Mock(spec=DeployCandidateBuild)
		step_pending = self._make_step(status="Pending")
		step_running = self._make_step(status="Running")
		build.build_steps = [step_pending, step_running]
		result = DeployCandidateBuild.get_first_step(build, "status", "Running")
		self.assertIs(result, step_running)

	def test_returns_first_step_matching_list_of_values(self):
		build = Mock(spec=DeployCandidateBuild)
		step = self._make_step(status="Running")
		build.build_steps = [step]
		result = DeployCandidateBuild.get_first_step(build, "status", ["Running", "Pending"])
		self.assertIs(result, step)

	def test_returns_none_when_no_step_matches(self):
		build = Mock(spec=DeployCandidateBuild)
		build.build_steps = [self._make_step(status="Success")]
		self.assertIsNone(DeployCandidateBuild.get_first_step(build, "status", "Running"))


class TestBuildDurationCapping(FrappeTestCase):
	"""Tests for the MAX_DURATION cap applied to build durations.

	Builds that hang for >24 h would produce invalid Time field values;
	we cap at 23:59:59 before saving. These tests verify the min() guard.
	"""

	def test_duration_exceeding_max_is_capped(self):
		from press.press.doctype.deploy_candidate_build.deploy_candidate_build import MAX_DURATION

		build = Mock(spec=DeployCandidateBuild)
		start = datetime(2024, 1, 1, 0, 0, 0)
		end = datetime(2024, 1, 2, 5, 0, 0)  # 29 hours — exceeds MAX_DURATION
		build.build_start = start

		with patch(
			"press.press.doctype.deploy_candidate_build.deploy_candidate_build.now",
			return_value=end,
		):
			DeployCandidateBuild._set_build_duration(build)

		self.assertEqual(build.build_duration, MAX_DURATION)

	def test_normal_duration_is_stored_as_is(self):
		build = Mock(spec=DeployCandidateBuild)
		start = datetime(2024, 1, 1, 10, 0, 0)
		end = datetime(2024, 1, 1, 10, 30, 0)  # 30 minutes — well within cap
		build.build_start = start

		with patch(
			"press.press.doctype.deploy_candidate_build.deploy_candidate_build.now",
			return_value=end,
		):
			DeployCandidateBuild._set_build_duration(build)

		self.assertEqual(build.build_duration, timedelta(minutes=30))


class TestUpdateStatusFromRemoteBuildJob(FrappeTestCase):
	"""Tests for _update_status_from_remote_build_job — the job-status→build-status mapping.

	This match statement is the single point that translates remote agent job
	outcomes into build states. A wrong mapping would silently mark failed builds
	as successful (or vice-versa).
	"""

	@staticmethod
	def _make_build() -> Mock:
		build = Mock(spec=DeployCandidateBuild)
		build.set_status = Mock()
		build._set_build_duration = Mock()
		return build

	def test_pending_job_sets_running_without_recording_duration(self):
		build = self._make_build()
		DeployCandidateBuild._update_status_from_remote_build_job(build, Mock(status="Pending"))
		build.set_status.assert_called_once_with(Status.RUNNING)
		build._set_build_duration.assert_not_called()

	def test_running_job_sets_running_without_recording_duration(self):
		build = self._make_build()
		DeployCandidateBuild._update_status_from_remote_build_job(build, Mock(status="Running"))
		build.set_status.assert_called_once_with(Status.RUNNING)
		build._set_build_duration.assert_not_called()

	def test_failure_job_records_duration_then_sets_failure(self):
		build = self._make_build()
		DeployCandidateBuild._update_status_from_remote_build_job(build, Mock(status="Failure"))
		build._set_build_duration.assert_called_once()
		build.set_status.assert_called_once_with(Status.FAILURE)

	def test_undelivered_job_is_treated_as_failure(self):
		build = self._make_build()
		DeployCandidateBuild._update_status_from_remote_build_job(build, Mock(status="Undelivered"))
		build.set_status.assert_called_once_with(Status.FAILURE)

	def test_success_job_records_duration_then_sets_success(self):
		build = self._make_build()
		DeployCandidateBuild._update_status_from_remote_build_job(build, Mock(status="Success"))
		build._set_build_duration.assert_called_once()
		build.set_status.assert_called_once_with(Status.SUCCESS)


class TestValidateStatus(FrappeTestCase):
	"""Tests for validate_status — guards against retrying mid-flight builds.

	Calling pre_build on an in-progress build would queue duplicate work;
	validate_status is the only gate preventing that.
	"""

	@staticmethod
	def _make_build(status: str) -> Mock:
		build = Mock(spec=DeployCandidateBuild)
		build.status = status
		return build

	def test_retryable_statuses_return_true(self):
		for status in ["Draft", "Success", "Failure", "Scheduled"]:
			with self.subTest(status=status):
				self.assertTrue(DeployCandidateBuild.validate_status(self._make_build(status)))

	def test_in_progress_statuses_raise_validation_error(self):
		for status in ["Pending", "Running", "Preparing"]:
			with self.subTest(status=status), self.assertRaises(frappe.ValidationError):
				DeployCandidateBuild.validate_status(self._make_build(status))


@patch("press.press.doctype.deploy_candidate.deploy_candidate.frappe.db.commit")
@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestCanRetryBuild(FrappeTestCase):
	"""Tests for can_retry_build - requires DB records."""

	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		app = create_test_app()
		self.build_server = create_test_server(platform="x86_64", use_for_build=True)
		group = create_test_release_group([app], self.team.user)
		group.db_set("team", self.team.name)
		frappe.set_user(self.team.user)
		self.deploy_candidate = create_test_deploy_candidate(group)
		self.group_name = group.name

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_can_retry_when_started_today_and_no_later_builds(self, _commit):
		build = create_test_deploy_candidate_build(self.deploy_candidate)
		build.run_build = False  # after_insert calls pre_build when run_build=1 (the doctype default)
		build.insert()
		build.db_set("build_start", frappe.utils.now_datetime())
		build.reload()

		self.assertTrue(can_retry_build(build.name, self.group_name, build.build_start))

	def test_cannot_retry_when_build_started_yesterday(self, _commit):
		yesterday = frappe.utils.add_days(frappe.utils.now_datetime(), -1)
		build = create_test_deploy_candidate_build(self.deploy_candidate)
		build.run_build = False
		build.insert()

		self.assertFalse(can_retry_build(build.name, self.group_name, yesterday))


class TestPlatformBuildGating(FrappeTestCase):
	"""create_new_platform_build_if_required_and_deploy controls whether the other
	platform gets a build and whether the deploy fires.

	If this guard breaks (e.g. condition flipped), the system would either:
	- Deploy using an incomplete image set (Intel image to ARM servers)
	- Never trigger the deploy even after both images are ready
	- Spawn duplicate builds for an already-satisfied platform

	All three are silent operational failures — no exception, just wrong behavior.
	"""

	def _make_build(self, status=None, platform="x86_64"):
		"""Return a Mock DeployCandidateBuild with candidate attached."""
		build = Mock(spec=DeployCandidateBuild)
		build.status = status or Status.SUCCESS.value
		build.platform = platform
		build.no_build = False
		build.no_cache = False
		build.no_push = False
		build.create_deploy = Mock()

		candidate = Mock()
		candidate.name = "test-dc"
		candidate.requires_arm_build = False
		candidate.arm_build = None
		candidate.requires_intel_build = False
		candidate.intel_build = None
		build.candidate = candidate
		return build

	def _call(self, build, deploy_after_build=True):
		captured = []

		def fake_get_doc(meta):
			doc = Mock()
			doc.insert = Mock()
			captured.append(dict(meta))
			return doc

		with patch("frappe.get_doc", side_effect=fake_get_doc):
			DeployCandidateBuild.create_new_platform_build_if_required_and_deploy(
				build, deploy_after_build=deploy_after_build
			)

		return captured

	def test_arm_build_spawned_when_required_and_missing(self):
		build = self._make_build(platform="x86_64")
		build.candidate.requires_arm_build = True
		build.candidate.arm_build = None  # not yet built

		created = self._call(build)

		self.assertEqual(len(created), 1)
		self.assertEqual(created[0]["platform"], "arm64")
		build.create_deploy.assert_not_called()  # deploy must not fire yet

	def test_intel_build_spawned_when_required_and_missing(self):
		build = self._make_build(platform="arm64")
		build.candidate.requires_intel_build = True
		build.candidate.intel_build = None

		created = self._call(build)

		self.assertEqual(len(created), 1)
		self.assertEqual(created[0]["platform"], "x86_64")
		build.create_deploy.assert_not_called()

	def test_no_build_spawned_when_both_platforms_already_satisfied(self):
		build = self._make_build()
		build.candidate.requires_arm_build = True
		build.candidate.arm_build = "some-arm-build"  # already done
		build.candidate.requires_intel_build = True
		build.candidate.intel_build = "some-intel-build"  # already done

		created = self._call(build, deploy_after_build=True)

		self.assertEqual(created, [])  # nothing new spawned
		build.create_deploy.assert_called_once()  # deploy should fire

	def test_deploy_fires_only_on_success_not_failure(self):
		build = self._make_build(status=Status.FAILURE.value)
		# Both platforms satisfied, but this build failed
		build.candidate.requires_arm_build = True
		build.candidate.arm_build = "some-arm-build"
		build.candidate.requires_intel_build = False

		self._call(build, deploy_after_build=True)

		build.create_deploy.assert_not_called()

	def test_deploy_does_not_fire_when_deploy_after_build_is_false(self):
		build = self._make_build(status=Status.SUCCESS.value)
		# No additional platform required — would normally deploy
		build.candidate.requires_arm_build = False
		build.candidate.requires_intel_build = False

		self._call(build, deploy_after_build=False)

		build.create_deploy.assert_not_called()

	def test_no_duplicate_arm_build_when_arm_already_assigned(self):
		build = self._make_build(platform="x86_64")
		build.candidate.requires_arm_build = True
		build.candidate.arm_build = "already-built-arm"  # already assigned

		created = self._call(build, deploy_after_build=False)

		# arm_build already present → no new ARM build should be created
		arm_builds = [d for d in created if d.get("platform") == "arm64"]
		self.assertEqual(arm_builds, [])
