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

	def test_final_sync_clears_db_lsyncd_state_before_play_so_any_retry_starts_lsyncd_again(self):
		failover = frappe.get_doc({"doctype": "On-Prem Failover", "is_lsyncd_running_for_db": 1})
		calls = MagicMock()
		calls.run.return_value.status = "Failure"
		with (
			patch(
				"press.press.doctype.on_prem_failover.on_prem_failover.Ansible",
				return_value=MagicMock(run=calls.run),
			),
			patch.object(OnPremFailover, "database_server_doc", new_callable=PropertyMock),
			patch.object(OnPremFailover, "db_set", calls.db_set),
			self.assertRaisesRegex(frappe.ValidationError, "Failed to perform the final database sync"),
		):
			failover._setup_db_rsync_for_final_sync()

		self.assertEqual([c[0] for c in calls.mock_calls[:2]], ["db_set", "run"])
		self.assertEqual(
			calls.db_set.call_args.args[0],
			{"is_lsyncd_running_for_db": False, "db_lsyncd_started_on": None, "db_lsyncd_stop_at": None},
		)
