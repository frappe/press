# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.test_agent_job import create_test_agent_job


class TestProductTrialRequest(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _trial_request_waiting_on(self, status):
		job = create_test_agent_job(job_type="Add Domain", status=status, job_id=42)
		trial_request = frappe.get_doc({"doctype": "Product Trial Request", "agent_job": job.name})
		trial_request.db_insert()
		return trial_request, job

	@patch("press.press.doctype.agent_job.agent_job.handle_polled_job")
	@patch("press.agent.Agent.raw_request", return_value={"id": 42, "status": "Success"})
	def test_finished_job_is_handled_without_waiting_for_the_poll(self, raw_request, handle_polled_job):
		trial_request, job = self._trial_request_waiting_on("Running")

		self.assertTrue(trial_request.refresh_current_agent_job())

		raw_request.assert_called_once_with("GET", "jobs/42", timeout=(2, 5))
		self.assertEqual(handle_polled_job.call_args.kwargs["job"].name, job.name)

	@patch("press.press.doctype.agent_job.agent_job.handle_polled_job")
	@patch("press.agent.Agent.raw_request", return_value={"id": 42, "status": "Running"})
	def test_unchanged_job_is_left_to_the_poll(self, raw_request, handle_polled_job):
		trial_request, _job = self._trial_request_waiting_on("Running")

		self.assertFalse(trial_request.refresh_current_agent_job())

		handle_polled_job.assert_not_called()

	@patch("press.press.doctype.agent_job.agent_job.handle_polled_job")
	@patch("press.agent.Agent.raw_request")
	def test_finished_job_is_not_fetched_again(self, raw_request, handle_polled_job):
		trial_request, _job = self._trial_request_waiting_on("Success")

		self.assertFalse(trial_request.refresh_current_agent_job())

		raw_request.assert_not_called()
		handle_polled_job.assert_not_called()

	@patch("press.press.doctype.agent_job.agent_job.handle_polled_job")
	@patch("press.agent.Agent.raw_request", side_effect=TimeoutError)
	def test_unreachable_agent_is_left_to_the_poll(self, raw_request, handle_polled_job):
		trial_request, _job = self._trial_request_waiting_on("Pending")

		self.assertFalse(trial_request.refresh_current_agent_job())

		handle_polled_job.assert_not_called()
