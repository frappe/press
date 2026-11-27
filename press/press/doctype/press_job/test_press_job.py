# Copyright (c) 2022, Frappe and Contributors
# See license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from press.agent import AgentRequestSkippedException
from press.press.doctype.ansible_play.test_ansible_play import create_test_ansible_play
from press.press.doctype.press_job.jobs.create_server import CreateServerJob
from press.press.doctype.press_job.jobs.increase_disk_size import IncreaseDiskSizeJob
from press.press.doctype.press_job.jobs.setup_agent_volume import SetupAgentVolumeJob
from press.press.doctype.press_job.jobs.trigger_build_server_cleanup import TriggerBuildServerCleanupJob
from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.press.doctype.server.server import BaseServer
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.server_plan.test_server_plan import create_test_server_plan
from press.press.doctype.telegram_message.telegram_message import TelegramMessage

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

		with patch("press.press.doctype.press_job.press_job.frappe.enqueue") as enqueue:
			job.alert_failure(workflow)

		message, channel = enqueue.call_args.kwargs["text"], enqueue.call_args.kwargs["channel"]
		self.assertIn("Resize Server failed", message)
		self.assertIn(self.server.name, message)
		self.assertIn("Stop Virtual Machine", message)
		self.assertEqual(channel, "frappe-cloud-server-alerts")

	def test_failed_create_server_job_is_alerted(self):
		job = self.create_job("Create Server")
		workflow = self.create_workflow(job)

		with patch("press.press.doctype.press_job.press_job.frappe.enqueue") as enqueue:
			job.alert_failure(workflow)

		enqueue.assert_called_once()
		self.assertIn("Unknown", enqueue.call_args.kwargs["text"])

	def test_failed_archive_server_job_is_alerted(self):
		job = self.create_job("Archive Server")
		workflow = self.create_workflow(job, failed_step="Archive Server")

		with patch("press.press.doctype.press_job.press_job.frappe.enqueue") as enqueue:
			job.alert_failure(workflow)

		enqueue.assert_called_once()

	def test_failed_setup_agent_volume_job_is_alerted(self):
		job = self.create_job("Setup Agent Volume")
		workflow = self.create_workflow(job, failed_step="Setup Agent Volume")

		with patch("press.press.doctype.press_job.press_job.frappe.enqueue") as enqueue:
			job.alert_failure(workflow)

		enqueue.assert_called_once()
		self.assertIn("Setup Agent Volume failed", enqueue.call_args.kwargs["text"])

	def test_other_failed_jobs_are_not_alerted(self):
		job = self.create_job("Increase Disk Size")
		workflow = self.create_workflow(job, failed_step="Increase Disk Size")

		with patch("press.press.doctype.press_job.press_job.frappe.enqueue") as enqueue:
			job.alert_failure(workflow)

		enqueue.assert_not_called()

	def test_no_alert_when_the_setting_disables_them(self):
		frappe.db.set_single_value("Press Settings", "disable_press_job_failure_alerts", 1)
		job = self.create_job("Resize Server")
		workflow = self.create_workflow(job, failed_step="Stop Virtual Machine")

		with patch("press.press.doctype.press_job.press_job.frappe.enqueue") as enqueue:
			job.alert_failure(workflow)

		enqueue.assert_not_called()


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


def make_create_server_job(server_type: str, has_data_volume: bool) -> CreateServerJob:
	job = CreateServerJob(
		{
			"doctype": "Press Job",
			"job_type": "Create Server",
			"server_type": server_type,
			"server": "f1-test.frappe.cloud",
		}
	)
	job._server_doc = Mock(has_data_volume=has_data_volume)
	return job


class TestCreateServerJobAgentVolume(FrappeTestCase):
	def test_agent_volume_set_up_on_app_and_unified_server_without_data_volume(self):
		job = make_create_server_job("Server", has_data_volume=False)
		job.setup_agent_volume()
		job.server_doc._setup_agent_volume.assert_called_once()

	def test_agent_volume_skipped_on_app_server_with_data_volume(self):
		job = make_create_server_job("Server", has_data_volume=True)
		job.setup_agent_volume()
		job.server_doc._setup_agent_volume.assert_not_called()

	def test_agent_volume_skipped_on_database_server(self):
		job = make_create_server_job("Database Server", has_data_volume=False)
		job.setup_agent_volume()
		job.server_doc._setup_agent_volume.assert_not_called()

	def test_failed_agent_volume_play_fails_the_create_server_job_step(self):
		job = make_create_server_job("Server", has_data_volume=False)
		job.server_doc._setup_agent_volume.side_effect = Exception("agent_volume.yml failed")
		with self.assertRaisesRegex(Exception, "agent_volume.yml failed"):
			job.setup_agent_volume()


def make_setup_agent_volume_job(server: str, age_hours: int) -> SetupAgentVolumeJob:
	return SetupAgentVolumeJob(
		{
			"doctype": "Press Job",
			"job_type": "Setup Agent Volume",
			"server_type": "Server",
			"server": server,
			"creation": add_to_date(now_datetime(), hours=-age_hours),
		}
	)


def make_agent_job(server: str, status: str, job_id: int) -> str:
	job = frappe.get_doc(
		{
			"doctype": "Agent Job",
			"server_type": "Server",
			"server": server,
			"job_type": "Backup Site",
			"status": status,
			"job_id": job_id,
			"request_method": "POST",
			"request_path": "benches",
		}
	)
	job.db_insert()  # insert() hooks need redis and deliver the job
	return job.name


@patch.object(SetupAgentVolumeJob, "defer_current_task")
@patch("press.press.doctype.press_job.jobs.setup_agent_volume.handle_polled_jobs")
@patch("press.press.doctype.press_job.jobs.setup_agent_volume.poll_random_jobs")
class TestSetupAgentVolumeJob(FrappeTestCase):
	def setUp(self):
		self.server = create_test_server()

	def tearDown(self):
		frappe.db.rollback()

	def test_waits_while_an_agent_job_runs(self, poll: Mock, _handle: Mock, defer: Mock):
		make_agent_job(self.server.name, status="Running", job_id=1)

		make_setup_agent_volume_job(self.server.name, age_hours=4).wait_for_agent_jobs()

		poll.assert_called_once()
		defer.assert_called_once()

	def test_does_not_wait_for_undelivered_agent_jobs(self, poll: Mock, _handle: Mock, defer: Mock):
		make_agent_job(self.server.name, status="Undelivered", job_id=0)

		make_setup_agent_volume_job(self.server.name, age_hours=1).wait_for_agent_jobs()

		poll.assert_not_called()
		defer.assert_not_called()

	def test_keeps_waiting_while_agent_is_unreachable(self, poll: Mock, _handle: Mock, defer: Mock):
		make_agent_job(self.server.name, status="Running", job_id=1)
		poll.side_effect = AgentRequestSkippedException("Previous 3 requests have failed.")

		make_setup_agent_volume_job(self.server.name, age_hours=1).wait_for_agent_jobs()

		defer.assert_called_once()

	def test_fails_when_agent_jobs_still_run_after_12_hours(self, _poll: Mock, _handle: Mock, defer: Mock):
		agent_job = make_agent_job(self.server.name, status="Running", job_id=1)

		with self.assertRaisesRegex(frappe.ValidationError, agent_job):
			make_setup_agent_volume_job(self.server.name, age_hours=13).wait_for_agent_jobs()
		defer.assert_not_called()

	def test_failed_job_resumes_agent_jobs_and_restores_agent(self, _poll: Mock, _handle: Mock, _defer: Mock):
		frappe.db.set_value("Server", self.server.name, "halt_agent_jobs", True)

		with patch("press.press.doctype.press_job.jobs.setup_agent_volume.frappe.enqueue_doc") as enqueue_doc:
			make_setup_agent_volume_job(self.server.name, age_hours=1).on_press_job_failure(Mock())

		self.assertFalse(frappe.db.get_value("Server", self.server.name, "halt_agent_jobs"))
		self.assertEqual(enqueue_doc.call_args.args, ("Server", self.server.name, "_restore_agent_directory"))

	def test_play_timeout_outlasts_agent_worker_stop_wait(self, _poll: Mock, _handle: Mock, _defer: Mock):
		"""Workers get up to 1500 seconds (stopwaitsecs) to stop."""
		self.assertGreater(SetupAgentVolumeJob.setup_agent_volume._timeout, 1500)


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


@patch.object(IncreaseDiskSizeJob, "defer_current_task")
class TestWaitForPartitionToResizeForAwsEc2(FrappeTestCase):
	def setUp(self):
		self.server = create_test_server()
		self.job = make_increase_disk_size_job(resized=True)
		self.job.server = self.server.name
		self.job.creation = now_datetime()

	def tearDown(self):
		frappe.db.rollback()

	def add_extend_play(self, status: str, created_before_job: bool = False):
		play = create_test_ansible_play(
			"Extend EC2 Volume", "extend_ec2_volume.yml", server=self.server.name, status=status
		)
		if created_before_job:
			play.db_set("creation", add_to_date(self.job.creation, days=-1), update_modified=False)

	def test_waits_when_only_an_earlier_resize_has_a_successful_extend_play(self, mock_defer: Mock):
		self.add_extend_play("Success", created_before_job=True)

		self.job.wait_for_partition_to_resize_for_aws_ec2()

		mock_defer.assert_called_once()

	def test_stops_waiting_once_the_extend_play_of_this_job_succeeds(self, mock_defer: Mock):
		self.add_extend_play("Success")

		self.job.wait_for_partition_to_resize_for_aws_ec2()

		mock_defer.assert_not_called()

	def test_raises_when_the_extend_play_of_this_job_fails(self, mock_defer: Mock):
		self.add_extend_play("Failure")

		with self.assertRaisesRegex(Exception, "Failed to extend EC2 volume"):
			self.job.wait_for_partition_to_resize_for_aws_ec2()

		mock_defer.assert_not_called()


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


class TestCreateServerJobFailure(FrappeTestCase):
	def setUp(self):
		create_test_press_settings()
		self.server = create_test_server(plan=create_test_server_plan().name)
		self.job = CreateServerJob(
			{
				"doctype": "Press Job",
				"job_type": "Create Server",
				"server_type": "Server",
				"server": self.server.name,
				"virtual_machine": self.server.virtual_machine,
			}
		)

	def tearDown(self):
		frappe.db.rollback()

	def test_server_marked_broken_and_billing_stopped_when_machine_was_terminated(self):
		frappe.db.set_value("Virtual Machine", self.server.virtual_machine, "status", "Terminated")

		self.job.on_press_job_failure(None)

		self.assertEqual(frappe.db.get_value("Server", self.server.name, "status"), "Broken")
		self.assertFalse(self.server.subscription.enabled)

	def test_server_and_billing_untouched_when_machine_is_still_running(self):
		self.job.on_press_job_failure(None)

		self.assertEqual(frappe.db.get_value("Server", self.server.name, "status"), "Active")
		self.assertTrue(self.server.subscription.enabled)

	@patch("press.press.doctype.database_server.database_server.Ansible")
	def test_unified_server_job_stops_when_mariadb_upgrade_fails(self, mock_ansible: Mock):
		# Going on would push 11.8-only variables to MariaDB 10.6, which then fails to start
		mock_ansible.return_value.run.return_value = Mock(status="Failure")
		self.server.db_set("is_unified_server", 1)

		with self.assertRaisesRegex(frappe.ValidationError, "Failed to upgrade MariaDB on server"):
			self.job.upgrade_mariadb()


def make_build_cleanup_job(age_minutes: int) -> TriggerBuildServerCleanupJob:
	return TriggerBuildServerCleanupJob(
		{
			"doctype": "Press Job",
			"job_type": "Trigger Build Server Cleanup",
			"server_type": "Server",
			"server": "rb-test.frappe.cloud",
			"creation": add_to_date(now_datetime(), minutes=-age_minutes),
		}
	)


@patch.object(TriggerBuildServerCleanupJob, "defer_current_task")
@patch(
	"press.press.doctype.press_job.jobs.trigger_build_server_cleanup.get_active_build_count_by_build_server",
	return_value={"rb-test.frappe.cloud": 2},
)
class TestTriggerBuildServerCleanupJob(FrappeTestCase):
	def test_prune_waits_while_builds_run_on_the_server(self, _builds: Mock, mock_defer: Mock):
		make_build_cleanup_job(age_minutes=5).wait_for_running_builds()

		mock_defer.assert_called_once()

	def test_prune_stops_waiting_for_builds_after_30_minutes(self, _builds: Mock, mock_defer: Mock):
		make_build_cleanup_job(age_minutes=31).wait_for_running_builds()

		mock_defer.assert_not_called()

	def test_prune_does_not_wait_when_no_builds_run_on_the_server(self, mock_builds: Mock, mock_defer: Mock):
		mock_builds.return_value = {"other.frappe.cloud": 3}
		make_build_cleanup_job(age_minutes=5).wait_for_running_builds()

		mock_defer.assert_not_called()
