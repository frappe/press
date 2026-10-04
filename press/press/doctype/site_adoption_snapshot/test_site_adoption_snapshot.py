# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_adoption_snapshot.site_adoption_snapshot import (
	new_counts,
	record_daily_snapshot,
	record_hourly_snapshot,
)
from press.press.doctype.site_update.test_site_update import create_test_site_update

MODULE = "press.press.doctype.site_adoption_snapshot.site_adoption_snapshot"


def create_group_with_sites_behind(public: bool = True) -> frappe._dict:
	"""A group with an old and a new bench on one server, and a site in each state behind."""
	group = create_test_release_group([create_test_app()], public=public)
	old_bench = create_test_bench(group=group, creation=add_days(now_datetime(), -5))
	new_bench = create_test_bench(group=group, server=old_bench.server)

	sites = frappe._dict(
		current=create_test_site(bench=new_bench.name).name,
		waiting=create_test_site(bench=old_bench.name).name,
		standby=create_test_site(bench=old_bench.name).name,
		auto_updates_off=create_test_site(bench=old_bench.name).name,
		failed=create_test_site(bench=old_bench.name).name,
	)
	frappe.db.set_value("Site", sites.standby, "is_standby", 1)
	frappe.db.set_value("Site", sites.auto_updates_off, "skip_auto_updates", 1)
	create_test_site_update(sites.failed, group.name, "Failure", ignore_validate=True)
	return frappe._dict(group=group.name, old_bench=old_bench, new_bench=new_bench, sites=sites)


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
@patch(f"{MODULE}.frappe.db.commit", new=MagicMock)
class TestSiteAdoptionSnapshot(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_hourly_snapshot_counts_a_public_group_by_why_its_sites_are_behind(self):
		fixture = create_group_with_sites_behind()

		record_hourly_snapshot()

		row = frappe.get_last_doc(
			"Site Adoption Snapshot", {"tier": "Hourly", "release_group": fixture.group}
		)
		self.assertEqual(row.group_type, "Public")
		self.assertEqual((row.current_sites, row.behind_sites, row.standby_behind), (1, 4, 1))
		self.assertEqual((row.waiting, row.auto_updates_off, row.failed_update), (2, 1, 1))
		self.assertEqual(row.old_benches, 1)

	def test_hourly_snapshot_leaves_out_private_groups(self):
		fixture = create_group_with_sites_behind(public=False)

		record_hourly_snapshot()

		self.assertFalse(frappe.db.exists("Site Adoption Snapshot", {"release_group": fixture.group}))

	def test_daily_snapshot_adds_up_the_groups_of_each_type(self):
		public_a, public_b, private = new_counts("Public"), new_counts("Public"), new_counts("Private")
		public_a.update(current_sites=3, behind_sites=1, waiting=1)
		public_b.update(current_sites=2, behind_sites=2, waiting=2)
		private.update(current_sites=7)
		counts = {"group-a": public_a, "group-b": public_b, "group-c": private}

		with patch(f"{MODULE}.count_sites_by_group", return_value=counts):
			record_daily_snapshot()

		row = frappe.get_last_doc("Site Adoption Snapshot", {"tier": "Daily", "group_type": "Public"})
		self.assertEqual((row.current_sites, row.behind_sites, row.waiting), (5, 3, 3))

	def test_daily_snapshot_prunes_hourly_rows_past_retention(self):
		old = self.insert_hourly_row(add_days(now_datetime(), -31))
		recent = self.insert_hourly_row(add_days(now_datetime(), -1))

		with patch(f"{MODULE}.count_sites_by_group", return_value={}):
			record_daily_snapshot()

		self.assertFalse(frappe.db.exists("Site Adoption Snapshot", old))
		self.assertTrue(frappe.db.exists("Site Adoption Snapshot", recent))

	def insert_hourly_row(self, timestamp) -> str:
		return (
			frappe.get_doc(
				{
					"doctype": "Site Adoption Snapshot",
					"timestamp": timestamp,
					"tier": "Hourly",
					"group_type": "Public",
				}
			)
			.insert()
			.name
		)
