# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import MagicMock, PropertyMock, patch

import frappe
from frappe.tests import UnitTestCase

from press.press.doctype.on_prem_failover.on_prem_failover import (
	OnPremFailover,
	estimate_initial_sync_seconds,
)


class UnitTestOnPremFailover(UnitTestCase):
	def test_initial_sync_estimate_treats_disk_used_as_kib(self):
		ten_gib_in_kib = 10 * 1024 * 1024
		# 10 GiB at 5 MiB/s
		self.assertEqual(estimate_initial_sync_seconds(ten_gib_in_kib), 2048)

	def test_failed_final_sync_clears_db_lsyncd_state_so_retry_starts_lsyncd_again(self):
		failover = frappe.get_doc(
			{
				"doctype": "On-Prem Failover",
				"is_lsyncd_running_for_db": 1,
				"db_lsyncd_started_on": "2026-10-29 19:59:50",
				"db_lsyncd_stop_at": "2026-10-29 20:00:05",
			}
		)
		ansible = MagicMock()
		ansible.return_value.run.return_value.status = "Failure"
		with (
			patch("press.press.doctype.on_prem_failover.on_prem_failover.Ansible", ansible),
			patch.object(OnPremFailover, "database_server_doc", new_callable=PropertyMock),
			patch.object(OnPremFailover, "save") as save,
			self.assertRaisesRegex(frappe.ValidationError, "Failed to perform the final database sync"),
		):
			failover._setup_db_rsync_for_final_sync()

		save.assert_called_once()
		self.assertFalse(failover.is_lsyncd_running_for_db)
		self.assertIsNone(failover.db_lsyncd_started_on)
		self.assertIsNone(failover.db_lsyncd_stop_at)
