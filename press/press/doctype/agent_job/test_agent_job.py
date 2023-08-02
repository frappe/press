# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import json
import frappe
import unittest
from unittest.mock import patch, Mock
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.test_site import create_test_bench, create_test_site

from press.press.doctype.team.test_team import create_test_press_admin_team
from press.agent import Agent


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
			mock_reload_nginx.call_count, frappe.db.count("Proxy Server", {"status": "Active"})
		)
