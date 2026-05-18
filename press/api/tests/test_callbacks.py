from unittest import TestCase
from unittest.mock import patch

import frappe

from press.api.callbacks import update_job


class TestUpdateJob(TestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch("press.api.callbacks.verify_agent")
	def test_update_job_returns_when_feature_flag_disabled(self, _mock_verify):
		with patch("frappe.db.get_single_value", return_value=0):
			result = update_job(job={"id": "123"}, server="test-server")

		self.assertIsNone(result)

	@patch("press.api.callbacks.verify_agent")
	def test_update_job_returns_when_job_is_missing(self, _mock_verify):
		with patch("frappe.db.get_single_value", return_value=1):
			result = update_job(job=None, server="test-server")

		self.assertIsNone(result)

	@patch("press.api.callbacks.verify_agent")
	@patch("frappe.enqueue")
	@patch("frappe.get_value")
	def test_update_job_enqueues_handle_polled_job(
		self,
		mock_get_value,
		mock_enqueue,
		_mock_verify,
	):
		mock_get_value.return_value = {
			"name": "job-1",
			"job_id": "123",
			"status": "Running",
			"callback_failure_count": 0,
			"job_type": "Deploy",
		}

		with patch("frappe.db.get_single_value", return_value=1):
			update_job(
				job={"id": "123"},
				server="test-server",
			)

		mock_enqueue.assert_called_once()
