import json
from unittest import TestCase
from unittest.mock import patch

import frappe

from press.api.callbacks import (
	retry_undelivered,
	update_job,
)


class TestCallbacks(TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_update_job_returns_when_job_missing(self):
		self.assertIsNone(update_job(job=None))

	@patch("press.api.callbacks.handle_polled_job")
	@patch("press.api.callbacks.verify_agent")
	@patch("frappe.get_value")
	def test_update_job_calls_handle_polled_job(
		self,
		mock_get_value,
		mock_verify,
		mock_handle_polled_job,
	):
		mock_verify.return_value = (
			"test-server",
			"Server",
		)

		mock_get_value.return_value = {
			"name": "job-1",
			"job_id": "123",
			"status": "Running",
			"callback_failure_count": 0,
			"job_type": "Deploy",
		}

		update_job(job=json.dumps({"id": "123"}))

		mock_handle_polled_job.assert_called_once()

	@patch("press.api.callbacks.retry_undelivered_jobs")
	@patch("press.api.callbacks.verify_agent")
	def test_retry_undelivered(
		self,
		mock_verify,
		mock_retry_jobs,
	):
		mock_verify.return_value = (
			"test-server",
			"Server",
		)

		retry_undelivered()

		mock_retry_jobs.assert_called_once()
