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
from press.press.doctype.site_update.test_site_update import create_test_site_update
from press.press.report.rollout_progress.rollout_progress import execute


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
class TestRolloutProgress(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_shows_sites_on_the_new_bench_and_still_behind_it_per_server(self):
		fixture = create_group_with_sites_behind()

		_, rows, *_ = execute({"deploy_candidate": fixture.new_bench.candidate})

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].bench, fixture.new_bench.name)
		self.assertEqual((rows[0].on_bench, rows[0].behind, rows[0].percent_on_bench), (1, 4, 20.0))

	def test_chart_adds_up_the_successful_moves_onto_the_candidate(self):
		fixture = create_group_with_sites_behind()
		for site in (fixture.sites.waiting, fixture.sites.standby):
			update = create_test_site_update(site, fixture.group, "Success", ignore_validate=True)
			frappe.db.set_value(
				"Site Update",
				update.name,
				{
					"destination_candidate": fixture.new_bench.candidate,
					"server": fixture.new_bench.server,
					"update_end": frappe.utils.now_datetime(),
				},
			)

		_, rows, _, chart, _ = execute({"deploy_candidate": fixture.new_bench.candidate})

		self.assertEqual(rows[0].moved, 2)
		self.assertEqual(chart["data"]["datasets"][0]["values"][-1], 2)

	def test_server_whose_new_bench_is_still_installing_has_nothing_behind_yet(self):
		fixture = create_group_with_sites_behind()
		frappe.db.set_value("Bench", fixture.new_bench.name, "status", "Installing")

		_, rows, _, _, summary = execute({"deploy_candidate": fixture.new_bench.candidate})

		self.assertEqual(
			(rows[0].bench_status, rows[0].behind, rows[0].percent_on_bench), ("Installing", None, None)
		)
		values = {card["label"]: card["value"] for card in summary}
		self.assertEqual(values["Sites Behind"], 0)
