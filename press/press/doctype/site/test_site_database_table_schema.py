# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.agent_job.test_agent_job import create_test_agent_job
from press.press.doctype.site.test_site import create_test_site


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestFetchDatabaseTableSchema(FrappeTestCase):
	def setUp(self):
		self.site = create_test_site()

	def tearDown(self):
		frappe.db.rollback()

	def _create_schema_job(self, status: str, minutes_ago: int) -> AgentJob:
		job = create_test_agent_job("Fetch Database Table Schema", server=self.site.server, status=status)
		job.db_set("site", self.site.name)
		creation = frappe.utils.add_to_date(None, minutes=-minutes_ago)
		frappe.db.set_value("Agent Job", job.name, "creation", creation, update_modified=False)
		return job

	def _reload_schema(self) -> Mock:
		with patch.object(Agent, "fetch_database_table_schema") as fetch:
			self.site.fetch_database_table_schema(reload=True)
		return fetch

	def test_reload_creates_no_job_while_a_20_minute_old_schema_job_is_still_pending(self):
		self._create_schema_job("Pending", minutes_ago=20)

		self.assertFalse(self._reload_schema().called)

	def test_reload_creates_a_job_when_the_pending_schema_job_is_older_than_30_minutes(self):
		self._create_schema_job("Pending", minutes_ago=40)

		self.assertTrue(self._reload_schema().called)
