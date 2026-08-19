# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from typing import TYPE_CHECKING, Literal, TypedDict
from unittest.mock import Mock, patch

import frappe
import responses
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob, fail_old_jobs, lock_doc_updated_by_job
from press.press.doctype.agent_job.agent_job_notifications import DOC_URLS, JobErr, get_details
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
from press.press.doctype.app_source.test_app_source import create_test_app_source
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.team.test_team import create_test_press_admin_team
from press.utils.test import foreground_enqueue, foreground_enqueue_doc

if TYPE_CHECKING:
	from collections.abc import Callable


def fn_appender(before_insert: Callable, prepare_agent_responses: Callable):
	def new_before_insert(self):
		before_insert(self)
		prepare_agent_responses(self)

	return new_before_insert


def before_insert(self):
	return None


def fake_agent_job_req(
	job_type: str | list[str] | dict,
	status: Literal["Success", "Pending", "Running", "Failure"] | None = None,
	data: dict | None = None,
	steps: list[StepDict] | None = None,
) -> Callable:
	"""
	Fake successful (or custom status) delivery for one or more job types.

	Args:
	    job_type:
	        - str → single job type
	        - list[str] → multiple job types (all share same status/data/steps)
	        - dict → {job_type: {"status": ..., "data": ..., "steps": ...}}
	    status: Status for single job type OR for all in list.
	    data: Data for single job type OR for all in list.
	    steps: Steps for single job type OR for all in list.
	"""  # noqa: E101
	# Normalize into dict form: {job_type: {"status": ..., "data": ..., "steps": ...}}
	if isinstance(job_type, dict):
		job_specs = {
			jt: {
				"status": spec.get("status", "Success"),
				"data": spec.get("data", {}),
				"steps": spec.get("steps", []),
			}
			for jt, spec in job_type.items()
		}
	elif isinstance(job_type, list):
		job_specs = {jt: {"status": status, "data": data or {}, "steps": steps or []} for jt in job_type}
	else:  # str
		job_specs = {job_type: {"status": status, "data": data or {}, "steps": steps or []}}

	if isinstance(job_type, dict) and data and steps:
		raise ValueError(
			"Cannot provide 'data' and 'steps' when job_type is a dict. "
			"Use job_type['job_type'] = {'status': ..., 'data': ..., 'steps': ...} instead."
		)

	job_polling_response: dict[int, dict] = dict()

	def _fake_bulk_polling(request):
		match = re.search(r"/agent/jobs/([\d,]+)", request.url)
		if match:
			job_ids_str = match.group(1)
			job_ids = [int(j) for j in job_ids_str.split(",")]
		else:
			job_ids = []

		output = []
		for job_id in job_ids:
			if job_id not in job_polling_response:
				continue
			output.append(job_polling_response[job_id])
		return (200, {"Content-Type": "application/json"}, json.dumps(output))

	responses.add_callback(
		responses.GET, re.compile(r"^https://[^/]+:443/agent/jobs/\d+(?:,\d+)+$"), callback=_fake_bulk_polling
	)

	def prepare_agent_responses(self):
		# Only fake jobs we have specs for
		if self.job_type not in job_specs:
			return

		spec = job_specs[self.job_type]
		job_id = int(make_autoname(".#"))
		steps_for_job = list(spec["steps"]) or []

		# Fill missing steps for this job type
		if steps_for_job:
			needed_steps = frappe.get_all("Agent Job Type Step", {"parent": self.job_type}, pluck="step_name")
			for step in needed_steps:
				if not any(step == s["name"] for s in steps_for_job):
					steps_for_job.append({"name": step, "status": "Success", "data": {}})

		# Add timestamps and other fields
		for step in steps_for_job:
			step["start"] = "2023-08-20 18:24:28.024885"
			step["data"] = step.get("data", {})
			if step["status"] in ["Success", "Failure"]:
				step["duration"] = "00:00:13.464445"
				step["end"] = "2023-08-20 18:24:41.489330"
			if step["status"] in ["Success", "Failure", "Running"]:
				step["start"] = "2023-08-20 18:24:28.024885"
				step["end"] = None
				step["duration"] = None
			if step["status"] in ["Skipped", "Pending"]:
				step["start"] = None
				step["end"] = None
				step["duration"] = None

		# Fake POST and DELETE
		responses.post(
			f"https://{self.server}:443/agent/{self.request_path}",
			json={"job": job_id},
			status=200,
		)
		responses.delete(
			f"https://{self.server}:443/agent/{self.request_path}",
			json={"job": job_id},
			status=200,
		)

		# Fake polling data
		job_polling_response[job_id] = {
			"data": spec["data"],
			# TODO: uncomment lines as needed and make new parameters #
			"duration": "00:00:13.496281",
			"output": spec["data"].get("output", ""),
			"end": "2023-08-20 18:24:41.506067",
			"id": job_id,
			"start": "2023-08-20 18:24:28.009786",
			"status": spec["status"],
			"steps": steps_for_job
			or [
				{
					"data": {},
					"duration": "00:00:13.464445",
					"end": "2023-08-20 18:24:41.489330",
					"name": self.job_type,
					"start": "2023-08-20 18:24:28.024885",
					"status": spec["status"],
				}
			],
		}
		# Fake GET polling
		responses.add(
			responses.GET,
			f"https://{self.server}:443/agent/jobs/{job_id!s}",
			json=job_polling_response[job_id],
			status=200,
		)

	global before_insert
	before_insert = fn_appender(before_insert, prepare_agent_responses)
	return before_insert


def create_test_agent_job(
	job_type: str = "Force Remove Zombie Benches",
	server: str | None = None,
	server_type: str = "Server",
	status: str = "Undelivered",
	job_id: int = 0,
) -> AgentJob:
	"""Create a test Agent Job doc."""
	from press.press.doctype.server.test_server import create_test_server

	if not server:
		server = create_test_server().name

	return frappe.get_doc(
		{
			"doctype": "Agent Job",
			"server": server,
			"server_type": server_type,
			"job_type": job_type,
			"status": status,
			"job_id": job_id,
			"request_method": "POST",
			"request_path": "benches",
			"request_data": "{}",
		}
	).insert(ignore_permissions=True)


class StepDict(TypedDict):
	name: str
	status: Literal["Success", "Pending", "Running", "Failure", "Skipped"]


@contextmanager
def fake_agent_job(
	job_type: str,
	status: Literal["Success", "Pending", "Running", "Failure"] = "Success",
	data: dict | None = None,
	steps: list[StepDict] | None = None,
):
	"""Fakes agent job request and response.

	HEADS UP: Don't use this when you're mocking enqueue_http_request in your test context
	"""
	with (
		responses.mock,
		patch.object(
			AgentJob,
			"before_insert",
			fake_agent_job_req(job_type, status, data, steps),
			create=True,
		),
		patch(
			"press.press.doctype.agent_job.agent_job.frappe.enqueue_doc",
			new=foreground_enqueue_doc,
		),
		patch(
			"press.press.doctype.agent_job.agent_job.frappe.enqueue",
			new=foreground_enqueue,
		),
		patch("press.press.doctype.agent_job.agent_job.frappe.db.commit", new=Mock()),
		patch("press.press.doctype.agent_job.agent_job.frappe.db.rollback", new=Mock()),
	):
		frappe.local.role_permissions = {}  # due to bug in FF related to only_if_creator docperm
		yield
		global before_insert
		before_insert = lambda self: None  # noqa


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestAgentJob(FrappeTestCase):
	def setUp(self):
		super().setUp()

		self.team = create_test_press_admin_team()
		self.team.allocate_credit_amount(1000, source="Prepaid Credits", remark="Test")
		self.team.payment_mode = "Prepaid Credits"
		self.team.save()

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	def test_lock_doc_updated_by_job_respects_hierarchy(self):
		"""
		Site > Bench > Server
		"""
		site = create_test_site()  # creates job
		site.update_site_config({"maintenance_mode": "1"})
		job = frappe.get_last_doc("Agent Job", {"job_type": "Update Site Configuration"})
		doc_name = lock_doc_updated_by_job(job.name)
		self.assertIsNone(doc_name)
		job = frappe.get_last_doc("Agent Job", {"job_type": "New Site"})
		doc_name = lock_doc_updated_by_job(job.name)
		self.assertEqual(site.name, doc_name)
		job.db_set("site", None)
		doc_name = lock_doc_updated_by_job(job.name)
		self.assertEqual(site.bench, doc_name)
		job.db_set("bench", None)
		doc_name = lock_doc_updated_by_job(job.name)
		self.assertEqual(site.server, doc_name)
		job.db_set("server", None)  # will realistically never happen
		doc_name = lock_doc_updated_by_job(job.name)
		self.assertIsNone(doc_name)

	@patch("press.press.doctype.site.site.create_dns_record", new=Mock())
	@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
	def test_lock_doc_updated_by_job_locks_on_site_rename(self):
		site = create_test_site()
		site.subdomain = "renamed-domain"
		site.save()
		job = frappe.get_last_doc("Agent Job", {"job_type": "Rename Site"})
		doc_name = lock_doc_updated_by_job(job.name)
		self.assertEqual(site.name, doc_name)
		job = frappe.get_last_doc("Agent Job", {"job_type": "Rename Site on Upstream"})
		doc_name = lock_doc_updated_by_job(job.name)
		self.assertEqual(site.name, doc_name)

	def _make_old(self, job_name: str):
		# Age the job past the 2-day cutoff that fail_old_jobs uses
		frappe.db.set_value("Agent Job", job_name, "creation", add_days(None, -3), update_modified=False)

	def test_fail_old_jobs_marks_stuck_running_job_as_failure(self):
		job = create_test_agent_job(status="Running", job_id=42)
		self._make_old(job.name)

		fail_old_jobs()

		self.assertEqual(frappe.db.get_value("Agent Job", job.name, "status"), "Failure")

	def test_fail_old_jobs_marks_undelivered_job_as_delivery_failure(self):
		job = create_test_agent_job(status="Undelivered", job_id=0)
		self._make_old(job.name)

		fail_old_jobs()

		self.assertEqual(frappe.db.get_value("Agent Job", job.name, "status"), "Delivery Failure")

	def test_no_duplicate_undelivered_job(self):
		site = create_test_site()
		site.update_site_config({"maintenance_mode": "1"})
		job = frappe.get_last_doc("Agent Job", {"job_type": "Update Site Configuration"})

		frappe.db.set_single_value("Press Settings", "disable_agent_job_deduplication", False)

		# create a new job with same type and site
		job_name = site.update_site_config({"host_name": f"https://{site.host_name}"})

		self.assertEqual(job_name.name, job.name)

	def test_get_similar_in_execution_job(self):
		site = create_test_site()
		site.update_site_config({"maintenance_mode": "1"})
		job = frappe.get_last_doc("Agent Job", {"job_type": "Update Site Configuration"})

		frappe.db.set_single_value("Press Settings", "disable_agent_job_deduplication", False)

		# check if similar job exists
		agent = Agent(site.server)
		in_execution_job = agent.get_similar_in_execution_job(
			job_type="Update Site Configuration",
			path=f"benches/{site.bench}/sites/{site.name}/config",
			bench=site.bench,
			site=site.name,
		)

		self.assertEqual(in_execution_job.name, job.name)

		frappe.db.set_single_value("Press Settings", "disable_agent_job_deduplication", True)


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestCancelJob(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_cancelling_a_finished_job_is_rejected(self):
		job = create_test_agent_job(job_type="Restore Site", status="Success", job_id=42)

		self.assertRaisesRegex(frappe.ValidationError, "job that is Success", job.cancel_job)

	def test_dashboard_cant_cancel_a_job_type_without_a_failure_path(self):
		job = create_test_agent_job(job_type="Migrate Site", status="Running", job_id=42)

		self.assertRaisesRegex(
			frappe.ValidationError,
			"Migrate Site jobs can't be cancelled",
			job.validate_dashboard_cancellation,
		)

	def test_dashboard_can_cancel_a_running_restore(self):
		job = create_test_agent_job(job_type="Restore Site", status="Running", job_id=42)

		job.validate_dashboard_cancellation()  # doesn't raise

	def test_dashboard_cant_cancel_a_site_update_that_skipped_backups(self):
		job = create_test_agent_job(job_type="Update Site Migrate", status="Running", job_id=42)
		site_update = frappe.get_doc(
			doctype="Site Update",
			name="test-site-update-cancel",
			status="Running",
			update_job=job.name,
			skipped_backups=1,
		)
		site_update.db_insert()

		self.assertRaisesRegex(
			frappe.ValidationError,
			"backups skipped",
			job.validate_dashboard_cancellation,
		)


class TestAgentJobNotifications(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	PKG_RESOURCES_TRACEBACK = (
		'  File "/home/frappe/frappe-bench/apps/frappe/frappe/__init__.py", line 1461, in get_module\n'
		'  File "/home/frappe/frappe-bench/apps/dummy_app/dummy_app/utils.py", line 6, in <module>\n'
		"    import razorpay\n"
		'  File "/home/frappe/frappe-bench/env/lib/python3.11/site-packages/razorpay/client.py", line 4, in <module>\n'
		"    import pkg_resources\n"
		"ModuleNotFoundError: No module named 'pkg_resources'"
	)

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_missing_pkg_resources_points_at_the_app_and_the_doc(self):
		site, bench = self.site_with_app("dummy_app", owned_by_site_team=False, newer_release=True)
		job = self.update_job(site, bench, self.PKG_RESOURCES_TRACEBACK)

		details = get_details(job, "", "")

		self.assertTrue(details["is_actionable"])
		self.assertEqual(details["title"], "Update failed because of the dummy_app app")
		self.assertIn("<code>pkg_resources</code>", details["message"])
		self.assertEqual(details["assistance_url"], DOC_URLS[JobErr.PKG_RESOURCES])

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_missing_pkg_resources_in_teams_own_app_points_at_the_same_doc(self):
		site, bench = self.site_with_app("dummy_app", newer_release=True)
		job = self.update_job(site, bench, self.PKG_RESOURCES_TRACEBACK)

		details = get_details(job, "", "")

		self.assertIn("<code>pkg_resources</code>", details["message"])
		self.assertEqual(details["assistance_url"], DOC_URLS[JobErr.PKG_RESOURCES])

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_missing_pkg_resources_gets_a_banner_even_when_the_app_is_on_its_latest_release(self):
		site, bench = self.site_with_app("dummy_app", owned_by_site_team=False)
		job = self.update_job(site, bench, self.PKG_RESOURCES_TRACEBACK)

		details = get_details(job, "", "")

		self.assertTrue(details["is_actionable"])
		self.assertEqual(details["assistance_url"], DOC_URLS[JobErr.PKG_RESOURCES])

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_known_traceback_wins_over_the_app_update_suggestion(self):
		site, bench = self.site_with_app("dummy_app", owned_by_site_team=False, newer_release=True)
		job = self.update_job(
			site,
			bench,
			'  File "/home/frappe/frappe-bench/apps/dummy_app/dummy_app/patches/fix_rates.py", line 12, in execute\n'
			"pymysql.err.OperationalError: (1118, 'Row size too large')",
		)

		details = get_details(job, "", "")

		self.assertEqual(details["title"], "Row size too large error")
		self.assertEqual(details["assistance_url"], DOC_URLS[JobErr.ROW_SIZE_TOO_LARGE])

	def test_missing_pkg_resources_on_a_job_without_bench_is_not_actionable(self):
		job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"job_type": "Update Agent",
				"server": "test.frappe.cloud",
				"traceback": "ImportError: Module import failed for Dropbox Settings, the DocType you're trying to open might be deleted.\nError: No module named 'pkg_resources'",
			}
		)

		details = get_details(job, "", "")

		self.assertFalse(details["is_actionable"])
		self.assertIsNone(details["assistance_url"])

	def site_with_app(
		self, app_name: str, owned_by_site_team: bool = True, newer_release: bool = False
	) -> tuple[str, str]:
		"""Site on a bench that has app_name installed"""
		frappe_app = create_test_app()
		other_app = create_test_app(app_name, app_name.title())
		app_source = create_test_app_source(
			"Version 14", other_app, repository_url=f"https://github.com/dummy/{app_name}"
		)
		group = create_test_release_group(
			[frappe_app, other_app],
			app_sources=[create_test_app_source("Version 14", frappe_app).name, app_source.name],
		)
		bench = create_test_bench(group=group)

		if newer_release:
			create_test_app_release(app_source)

		site = create_test_site(bench=bench.name)
		if not owned_by_site_team:
			app_source.db_set("team", self.team_other_than(site.team))

		return site.name, bench.name

	def team_other_than(self, team: str) -> str:
		"""Reuse an existing team, creating one per test gets rate limited"""
		return frappe.db.get_value("Team", {"name": ("!=", team), "enabled": 1}, "name")

	def update_job(self, site: str, bench: str, traceback: str) -> AgentJob:
		return frappe.get_doc(
			{
				"doctype": "Agent Job",
				"job_type": "Update Site Migrate",
				"site": site,
				"bench": bench,
				"traceback": traceback,
			}
		)

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_update_failing_inside_teams_own_app_asks_them_to_debug_it(self):
		site, bench = self.site_with_app("dummy_app")
		job = self.update_job(
			site,
			bench,
			'  File "/home/frappe/frappe-bench/apps/frappe/frappe/modules/patch_handler.py", line 90, in execute\n'
			'  File "/home/frappe/frappe-bench/apps/dummy_app/dummy_app/patches/fix_rates.py", line 12, in execute\n'
			"KeyError: 'rate'",
		)

		details = get_details(job, "", "")

		self.assertTrue(details["is_actionable"])
		self.assertEqual(details["title"], "Update failed because of the dummy_app app")
		self.assertIn("failed inside your app <b>dummy_app</b>", details["message"])
		self.assertEqual(details["assistance_url"], DOC_URLS[JobErr.APP_DEBUG])

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_update_failing_inside_someone_elses_app_suggests_updating_it(self):
		site, bench = self.site_with_app("dummy_app", owned_by_site_team=False, newer_release=True)
		job = self.update_job(
			site,
			bench,
			'  File "/home/frappe/frappe-bench/apps/dummy_app/dummy_app/patches/fix_rates.py", line 12, in execute\n'
			"KeyError: 'rate'",
		)

		details = get_details(job, "", "")

		self.assertTrue(details["is_actionable"])
		self.assertEqual(details["title"], "Update failed because of the dummy_app app")
		self.assertIn("newer release of <b>dummy_app</b> is available", details["message"])
		self.assertEqual(details["assistance_url"], DOC_URLS[JobErr.APP_UPDATE])

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_app_name_with_digits_is_not_skipped(self):
		site, bench = self.site_with_app("dummy_app2")
		job = self.update_job(
			site,
			bench,
			'  File "/home/frappe/frappe-bench/apps/frappe/frappe/modules/patch_handler.py", line 90, in execute\n'
			'  File "/home/frappe/frappe-bench/apps/dummy_app2/dummy_app2/patches/fix_rates.py", line 12, in execute\n'
			"KeyError: 'rate'",
		)

		details = get_details(job, "", "")

		self.assertEqual(details["title"], "Update failed because of the dummy_app2 app")
		self.assertEqual(details["assistance_url"], DOC_URLS[JobErr.APP_DEBUG])

	@patch.object(AgentJob, "enqueue_http_request", new=Mock())
	def test_someone_elses_app_already_on_latest_release_gets_no_banner(self):
		site, bench = self.site_with_app("dummy_app", owned_by_site_team=False)
		job = self.update_job(
			site,
			bench,
			'  File "/home/frappe/frappe-bench/apps/dummy_app/dummy_app/patches/fix_rates.py", line 12, in execute\n'
			"KeyError: 'rate'",
		)

		details = get_details(job, "", "")

		self.assertFalse(details["is_actionable"])
		self.assertIsNone(details["assistance_url"])
