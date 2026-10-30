# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import json
from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_job.jobs.increase_disk_size import IncreaseDiskSizeJob
from press.press.doctype.server.server import BaseServer
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.telegram_message.telegram_message import TelegramMessage


class TestPressJob(FrappeTestCase):
	pass


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
		server = create_test_server(auto_increase_storage=True)

		self.assertTrue(server.calculated_increase_disk_size(mountpoint="/"))
		mock_increase.assert_called_once()
