# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import json
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.press.doctype.press_job.jobs.increase_disk_size import IncreaseDiskSizeJob
from press.press.doctype.press_job.press_job import PressJob
from press.press.doctype.server.server import BaseServer
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.telegram_message.telegram_message import TelegramMessage


class TestArchiveServerJob(FrappeTestCase):
	def insert_job(self, server, job_type, **kwargs):
		with patch.object(PressJob, "start_workflow", return_value="test"):
			return frappe.get_doc(
				{
					"doctype": "Press Job",
					"job_type": job_type,
					"server_type": "Server",
					"server": server.name,
					**kwargs,
				}
			).insert()

	def insert_stuck_workflow(self, job_name):
		with patch(
			"press.workflow_engine.doctype.press_workflow.press_workflow.enqueue_workflow",
			new=lambda *args, **kwargs: None,
		):
			return frappe.get_doc(
				{
					"doctype": "Press Workflow",
					"linked_doctype": "Press Job",
					"linked_docname": job_name,
					"main_method_name": "execute",
					"main_method_title": "Execute",
					"status": "Queued",
				}
			).insert(ignore_permissions=True)

	def test_archive_allowed_while_another_job_runs(self):
		server = create_test_server(provider="AWS EC2")
		create_job = self.insert_job(server, "Create Server", status="Running")

		archive_job = self.insert_job(server, "Archive Server")

		self.assertEqual(frappe.db.get_value("Press Job", create_job.name, "status"), "Running")
		self.assertEqual(archive_job.server, server.name)

	def test_recent_duplicate_archive_is_blocked(self):
		server = create_test_server(provider="AWS EC2")
		self.insert_job(server, "Archive Server", status="Running")

		with self.assertRaises(frappe.ValidationError) as context:
			self.insert_job(server, "Archive Server")

		self.assertIn("An Archive Server job is already Running", str(context.exception))

	def test_stale_duplicate_archive_is_allowed(self):
		server = create_test_server(provider="AWS EC2")
		stale_archive_job = self.insert_job(server, "Archive Server", status="Running")
		frappe.db.set_value(
			"Press Job",
			stale_archive_job.name,
			"creation",
			add_to_date(now_datetime(), minutes=-31),
		)

		archive_job = self.insert_job(server, "Archive Server")

		self.assertEqual(archive_job.server, server.name)

	def test_other_jobs_still_blocked_by_running_job(self):
		server = create_test_server(provider="AWS EC2")
		self.insert_job(server, "Create Server", status="Running")

		with self.assertRaises(frappe.ValidationError) as context:
			self.insert_job(server, "Increase Disk Size")

		self.assertIn("A Create Server job is already Running", str(context.exception))

	@patch("press.press.doctype.press_job.jobs.archive_server.force_fail_stuck_job")
	def test_wait_for_active_jobs_defers_for_recent_job(self, mock_force_fail):
		server = create_test_server(provider="AWS EC2")
		self.insert_job(server, "Create Server", status="Running")
		archive_job = self.insert_job(server, "Archive Server")

		with patch.object(archive_job, "defer_current_task") as mock_defer:
			archive_job.wait_for_active_jobs()

		mock_defer.assert_called_once()
		mock_force_fail.assert_not_called()

	def test_wait_for_active_jobs_force_fails_stale_job(self):
		server = create_test_server(provider="AWS EC2")
		stuck_job = self.insert_job(server, "Increase Disk Size", status="Running")
		frappe.db.set_value(
			"Press Job",
			stuck_job.name,
			"creation",
			add_to_date(now_datetime(), minutes=-31),
		)
		workflow = self.insert_stuck_workflow(stuck_job.name)
		archive_job = self.insert_job(server, "Archive Server")

		with patch.object(archive_job, "defer_current_task") as mock_defer:
			archive_job.wait_for_active_jobs()

		self.assertTrue(frappe.db.get_value("Press Workflow", workflow.name, "is_force_failure_requested"))
		mock_defer.assert_called_once()

	@patch("press.press.doctype.press_job.jobs.archive_server.force_fail_stuck_job")
	def test_wait_for_active_jobs_proceeds_without_active_jobs(self, mock_force_fail):
		server = create_test_server(provider="AWS EC2")
		archive_job = self.insert_job(server, "Archive Server")

		with patch.object(archive_job, "defer_current_task") as mock_defer:
			archive_job.wait_for_active_jobs()

		mock_defer.assert_not_called()
		mock_force_fail.assert_not_called()


def make_increase_disk_size_job(resized: bool) -> IncreaseDiskSizeJob:
	job = IncreaseDiskSizeJob(
		{
			"doctype": "Press Job",
			"job_type": "Increase Disk Size",
			"server_type": "Server",
			"server": "f1-test.frappe.cloud",
			"arguments": json.dumps({"labels": {"mountpoint": "/"}}),
		}
	)
	job._server_doc = Mock(provider="AWS EC2", calculated_increase_disk_size=Mock(return_value=resized))
	return job


@patch.object(IncreaseDiskSizeJob, "restart_active_benches")
@patch.object(IncreaseDiskSizeJob, "wait_for_partition_to_resize_for_aws_ec2")
class TestIncreaseDiskSizeJob(FrappeTestCase):
	def test_benches_not_restarted_when_disk_not_increased(self, mock_wait: Mock, mock_restart: Mock):
		job = make_increase_disk_size_job(resized=False)
		job.execute()

		job.server_doc.calculated_increase_disk_size.assert_called_once_with(mountpoint="/")
		mock_wait.assert_not_called()
		mock_restart.assert_not_called()

	def test_benches_restarted_after_disk_increased(self, mock_wait: Mock, mock_restart: Mock):
		job = make_increase_disk_size_job(resized=True)
		job.execute()

		mock_wait.assert_called_once()
		mock_restart.assert_called_once()


@patch.object(TelegramMessage, "enqueue", new=Mock())
@patch("press.press.doctype.server.server.insert_addon_storage_log", new=Mock())
@patch.object(BaseServer, "size_to_increase_by_for_20_percent_available", new=Mock(return_value=50))
@patch.object(BaseServer, "disk_capacity", new=Mock(return_value=100 * 1024**3))
@patch.object(BaseServer, "free_space", new=Mock(return_value=5 * 1024**3))
@patch.object(BaseServer, "increase_disk_size_for_server")
class TestCalculatedIncreaseDiskSize(FrappeTestCase):
	def test_returns_false_when_auto_increase_disabled(self, mock_increase: Mock):
		server = create_test_server(auto_increase_storage=False)

		self.assertFalse(server.calculated_increase_disk_size(mountpoint="/"))
		mock_increase.assert_not_called()

	def test_returns_true_when_disk_increased(self, mock_increase: Mock):
		server = create_test_server(auto_increase_storage=True, provider="AWS EC2")

		self.assertTrue(server.calculated_increase_disk_size(mountpoint="/"))
		mock_increase.assert_called_once()

	def test_returns_false_and_names_provider_when_auto_increase_enabled_on_generic_server(
		self, mock_increase: Mock
	):
		server = create_test_server(auto_increase_storage=True, provider="Generic")

		with patch.object(TelegramMessage, "enqueue") as mock_telegram:
			self.assertFalse(server.calculated_increase_disk_size(mountpoint="/"))

		mock_increase.assert_not_called()
		self.assertIn("Press can't resize disks on provider Generic", mock_telegram.call_args.args[0])
