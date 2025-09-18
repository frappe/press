# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from typing import TYPE_CHECKING, Literal
from unittest.mock import Mock, patch

import frappe
import responses
from frappe.model.naming import make_autoname
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob, lock_doc_updated_by_job
from press.press.doctype.site.test_site import create_test_site
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


def fake_agent_job_req(  # noqa: C901
	job_type: str | list[str] | dict,
	status: Literal["Success", "Pending", "Running", "Failure"] | None = None,
	data: dict | None = None,
	steps: list[dict] | None = None,
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

	job_polling_response = dict()

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
			step["data"] = {}
			if step["status"] in ["Success", "Failure"]:
				step["duration"] = "00:00:13.464445"
				step["end"] = "2023-08-20 18:24:41.489330"
			if step["status"] in ["Success", "Failure", "Running"]:
				step["start"] = "2023-08-20 18:24:28.024885"
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


@contextmanager
def fake_agent_job(
	job_type: str,
	status: Literal["Success", "Pending", "Running", "Failure"] = "Success",
	data: dict | None = None,
	steps: list[dict] | None = None,
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
