# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site_adoption_snapshot.test_site_adoption_snapshot import (
	create_group_with_sites_behind,
)
from press.press.report.update_laggards.update_laggards import execute


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestUpdateLaggards(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_lists_each_site_behind_with_why_it_has_not_moved(self):
		fixture = create_group_with_sites_behind()

		_, rows, *_ = execute({"release_group": fixture.group})

		reasons = {row.site: row.reason for row in rows}
		self.assertEqual(
			reasons,
			{
				fixture.sites.waiting: "Waiting",
				fixture.sites.standby: "Waiting",
				fixture.sites.auto_updates_off: "Auto Updates Off",
				fixture.sites.failed: "Failed Update",
			},
		)

	def test_reason_filter_keeps_only_sites_blocked_for_that_reason(self):
		fixture = create_group_with_sites_behind()

		_, rows, *_ = execute({"release_group": fixture.group, "reason": "Failed Update"})

		self.assertEqual([row.site for row in rows], [fixture.sites.failed])

	def test_site_behind_counts_its_days_from_when_the_newest_bench_was_created(self):
		fixture = create_group_with_sites_behind()
		frappe.db.set_value(
			"Bench",
			fixture.new_bench.name,
			"creation",
			frappe.utils.add_days(frappe.utils.now_datetime(), -2),
		)

		_, rows, *_ = execute({"release_group": fixture.group})

		self.assertTrue(all(row.days_behind == 2 for row in rows))
