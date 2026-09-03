# Copyright (c) 2022, Frappe and Contributors
# See license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.server.test_server import create_test_server

if TYPE_CHECKING:
	from press.press.doctype.press_job.press_job import PressJob


class TestPressJob(FrappeTestCase):
	def setUp(self):
		self.server = create_test_server()

	def tearDown(self):
		frappe.db.rollback()

	def create_job(self, job_type: str) -> PressJob:
		job = frappe.get_doc(
			{
				"doctype": "Press Job",
				"job_type": job_type,
				"server_type": "Server",
				"server": self.server.name,
				"arguments": json.dumps({}),
			}
		)
		job.db_insert()
		job.reload()
		return job

	def create_workflow(self, job: PressJob, failed_step: str | None = None):
		workflow = frappe.get_doc(
			{
				"doctype": "Press Workflow",
				"linked_doctype": "Press Job",
				"linked_docname": job.name,
				"main_method_name": "execute",
				"status": "Failure",
			}
		)
		workflow.db_insert()

		if failed_step:
			task = frappe.get_doc(
				{
					"doctype": "Press Workflow Task",
					"workflow": workflow.name,
					"method_name": "a_step",
					"method_title": failed_step,
					"status": "Failure",
				}
			)
			task.db_insert()

		return workflow

	def test_failed_resize_server_job_names_the_server_and_the_failed_step(self):
		job = self.create_job("Resize Server")
		workflow = self.create_workflow(job, failed_step="Stop Virtual Machine")

		with patch("press.press.doctype.press_job.press_job.send_raven_message") as send_raven_message:
			job.alert_failure(workflow)

		message, channel = send_raven_message.call_args[0]
		self.assertIn("Resize Server failed", message)
		self.assertIn(self.server.name, message)
		self.assertIn("Stop Virtual Machine", message)
		self.assertEqual(channel, "frappe-cloud-server-alerts")

	def test_failed_create_server_job_is_alerted(self):
		job = self.create_job("Create Server")
		workflow = self.create_workflow(job)

		with patch("press.press.doctype.press_job.press_job.send_raven_message") as send_raven_message:
			job.alert_failure(workflow)

		send_raven_message.assert_called_once()
		self.assertIn("Unknown", send_raven_message.call_args[0][0])

	def test_failed_archive_server_job_is_alerted(self):
		job = self.create_job("Archive Server")
		workflow = self.create_workflow(job, failed_step="Archive Server")

		with patch("press.press.doctype.press_job.press_job.send_raven_message") as send_raven_message:
			job.alert_failure(workflow)

		send_raven_message.assert_called_once()

	def test_other_failed_jobs_are_not_alerted(self):
		job = self.create_job("Increase Disk Size")
		workflow = self.create_workflow(job, failed_step="Increase Disk Size")

		with patch("press.press.doctype.press_job.press_job.send_raven_message") as send_raven_message:
			job.alert_failure(workflow)

		send_raven_message.assert_not_called()
