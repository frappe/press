# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from frappe.tests import UnitTestCase

from press.press.doctype.on_prem_failover.on_prem_failover import estimate_initial_sync_seconds


class UnitTestOnPremFailover(UnitTestCase):
	def test_initial_sync_estimate_treats_disk_used_as_kib(self):
		ten_gib_in_kib = 10 * 1024 * 1024
		# 10 GiB at 5 MiB/s
		self.assertEqual(estimate_initial_sync_seconds(ten_gib_in_kib), 2048)
