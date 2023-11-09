# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import json
from typing import Callable, Literal
from contextlib import contextmanager
import frappe
import unittest
from unittest.mock import patch, Mock

from frappe.model.naming import make_autoname
from press.press.doctype.agent_job.agent_job import AgentJob, lock_doc_updated_by_job
from press.press.doctype.site.test_site import create_test_bench, create_test_site

from press.press.doctype.team.test_team import create_test_press_admin_team
from press.agent import Agent

import responses

from press.utils.test import foreground_enqueue, foreground_enqueue_doc


def fn_appender(before_insert: Callable, prepare_agent_responses: Callable):
	def new_before_insert(self):
		before_insert(self)
		prepare_agent_responses(self)

	return new_before_insert


before_insert: Callable = lambda self: None


def fake_agent_job_req(
	job_type: str,
	status: Literal["Success", "Pending", "Running", "Failure"],
	data: dict,
	steps: list[dict],
) -> Callable:
	data = data or {}
	steps = steps or []

	def prepare_agent_responses(self):
		"""
		Fake successful delivery with fake job id

		Also return fake result on polling
		steps: list of {"name": "Step name", "status": "status"} dictionaries
		"""
		nonlocal status
		nonlocal job_type
		if self.job_type != job_type:  # only fake the job we want to fake
			return
		job_id = int(make_autoname(".#"))
		if steps:
			needed_steps = frappe.get_all(
				"Agent Job Type Step", {"parent": job_type}, pluck="step_name"
			)
			for step in needed_steps:
				if not any(step == s["name"] for s in steps):
					steps.append(
						{
							"name": step,
							"status": "Success",
							"data": {},
						}
					)

		for step in steps:
			step["start"] = "2023-08-20 18:24:28.024885"
			step["data"] = {}
			if step["status"] in ["Success", "Failure"]:
				step["duration"] = "00:00:13.464445"
				step["end"] = "2023-08-20 18:24:41.489330"
			if step["status"] in ["Success", "Failure", "Running"]:
				step["start"] = "2023-08-20 18:24:28.024885"
				step["end"] = None
				step["duration"] = None

		# TODO: auto add response corresponding to request type #
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
		# TODO: make the next url regex for multiple job ids #
		responses.add(
			responses.GET,
			f"https://{self.server}:443/agent/jobs/{str(job_id)}",
			# TODO:  populate steps with data from agent job type #
			json={
				"data": data,
				# TODO: uncomment lines as needed and make new parameters #
				"duration": "00:00:13.496281",
				"end": "2023-08-20 18:24:41.506067",
				# "enqueue": "2023-08-20 18:24:27.907340",
				"id": job_id,
				# "name": "Install App on Site",
				"start": "2023-08-20 18:24:28.009786",
				"status": status,
				"steps": steps
				or [
					{
						"data": {
							# "command": "docker exec -w /home/frappe/frappe-bench	bench-0001-000025-f1 bench --site fdesk-old.local.frappe.dev install-app helpdesk",
							# "directory": "/home/frappe/benches/bench-0001-000025-f1",
							# "duration": "0:00:13.447104",
							# "end": "2023-08-20 18:24:41.482031",
							# "output": "Installing helpdesk...\nUpdating DocTypes for helpdesk\t	 : [========================================] 100%\nUpdating Dashboard for helpdesk",
							# "start": "2023-08-20 18:24:28.034927",
						},
						"duration": "00:00:13.464445",
						"end": "2023-08-20 18:24:41.489330",
						# "id": 1350,
						"name": job_type,
						"start": "2023-08-20 18:24:28.024885",
						"status": status,
					}
				],
			},
			status=200,
		)

	global before_insert
	before_insert = fn_appender(before_insert, prepare_agent_responses)
	return before_insert


@contextmanager
def fake_agent_job(
	job_type: str,
	status: Literal["Success", "Pending", "Running", "Failure"] = "Success",
	data: dict = None,
	steps: list[dict] = None,
):
	"""Fakes agent job request and response. Also polls the job.

	HEADS UP: Don't use this when you're mocking enqueue_http_request in your test context
	"""
	with responses.mock, patch.object(
		AgentJob,
		"before_insert",
		fake_agent_job_req(job_type, status, data, steps),
		create=True,
	), patch(
		"press.press.doctype.agent_job.agent_job.frappe.enqueue_doc",
		new=foreground_enqueue_doc,
	), patch(
		"press.press.doctype.agent_job.agent_job.frappe.enqueue",
		new=foreground_enqueue,
	), patch(
		"press.press.doctype.agent_job.agent_job.frappe.db.commit", new=Mock()
	), patch(
		"press.press.doctype.agent_job.agent_job.frappe.db.rollback", new=Mock()
	):
		frappe.local.role_permissions = (
			{}
		)  # due to bug in FF related to only_if_creator docperm
		yield
		global before_insert
		before_insert = lambda self: None  # noqa


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
class TestAgentJob(unittest.TestCase):
	def setUp(self):
		self.team = create_test_press_admin_team()
		self.team.allocate_credit_amount(1000, source="Prepaid Credits", remark="Test")

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")

	@patch.object(Agent, "reload_nginx")
	def test_suspend_sites_issues_reload_in_bulk(self, mock_reload_nginx):
		from .agent_job import suspend_sites

		bench1 = create_test_bench()
		bench2 = create_test_bench()
		bench3 = create_test_bench()

		frappe.set_user(self.team.user)
		site1 = create_test_site(bench=bench1)
		site2 = create_test_site(bench=bench2)
		create_test_site(bench=bench3)  # control; no suspend

		site1.db_set("current_database_usage", 101)
		site2.db_set("current_disk_usage", 101)
		frappe.db.set_single_value("Press Settings", "enforce_storage_limits", True)
		suspend_sites()
		suspend_jobs = frappe.get_all(
			"Agent Job", {"job_type": "Update Site Status"}, ["request_data"]
		)
		for job in suspend_jobs:
			self.assertTrue(json.loads(job.request_data).get("skip_reload"))

		self.assertEqual(len(suspend_jobs), 2)
		self.assertEqual(
			mock_reload_nginx.call_count,
			frappe.db.count("Proxy Server", {"status": "Active"}),
		)

	def test_lock_doc_updated_by_job_respects_hierarchy(self):
		"""
		Site > Bench > Server
		"""
		site = create_test_site()  # creates job
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
