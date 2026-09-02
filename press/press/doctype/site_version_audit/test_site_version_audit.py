# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.release_group.test_release_group import create_test_release_group
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_update.test_site_update import create_test_site_update
from press.press.doctype.site_version_audit.site_version_audit import (
	count_sites_by_version_and_age,
	count_sites_by_version_and_age_on,
	record_audit,
)


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
@patch("press.press.doctype.site.site._change_dns_record", new=Mock())
@patch(
	"press.press.doctype.site_version_audit.site_version_audit.frappe.db.commit",
	new=MagicMock,
)
class TestSiteVersionAudit(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_audit_bands_a_site_by_the_age_of_its_frappe_release(self):
		site = self.create_site_with_frappe_released_days_ago(95)

		self.assertIn(90, self.bands_for(count_sites_by_version_and_age(), site))

	def test_audit_bands_a_recently_released_site_at_zero(self):
		site = self.create_site_with_frappe_released_days_ago(3)

		self.assertIn(0, self.bands_for(count_sites_by_version_and_age(), site))

	def test_audit_caps_the_oldest_band_at_a_year(self):
		site = self.create_site_with_frappe_released_days_ago(900)

		self.assertIn(360, self.bands_for(count_sites_by_version_and_age(), site))

	def test_audit_falls_back_to_when_the_release_was_recorded(self):
		site = self.create_site_with_frappe_released_days_ago(95, clear_commit_time=True)

		self.assertIn(90, self.bands_for(count_sites_by_version_and_age(), site))

	def test_record_audit_replaces_the_rows_for_the_day_instead_of_adding_to_them(self):
		self.create_site_with_frappe_released_days_ago(95)

		record_audit()
		first = frappe.db.count("Site Version Audit", {"date": frappe.utils.today()})
		record_audit()
		second = frappe.db.count("Site Version Audit", {"date": frappe.utils.today()})

		self.assertEqual(first, second)

	def test_audit_for_a_past_date_uses_the_bench_the_site_was_on_then(self):
		"""A site moved yesterday must be reported on its old bench for last month."""
		site = self.create_site_with_frappe_released_days_ago(3)
		old_bench = site.bench
		# the site has to predate the month being asked about
		frappe.db.set_value(
			"Site", site.name, "creation", frappe.utils.add_days(frappe.utils.now_datetime(), -60)
		)
		self.move_site_to_a_fresh_bench(site, frappe_released_days_ago=400)

		month_end = frappe.utils.add_days(frappe.utils.today(), -30)
		bands = self.bands_for(count_sites_by_version_and_age_on(month_end), site)

		self.assertNotEqual(site.reload().bench, old_bench)
		self.assertIn(0, bands)

	def test_audit_for_a_past_date_skips_sites_that_did_not_exist_yet(self):
		self.create_site_with_frappe_released_days_ago(3)

		before_any_site = frappe.utils.add_days(frappe.utils.today(), -3650)

		counts = count_sites_by_version_and_age_on(before_any_site)

		self.assertEqual(sum(row.sites for row in counts), 0)

	def move_site_to_a_fresh_bench(self, site: Site, frappe_released_days_ago: int):
		"""Record a completed move, which freezes the bench the site came from."""
		group = frappe.db.get_value("Site", site.name, "group")
		destination = create_test_bench(group=frappe.get_doc("Release Group", group))
		release = frappe.db.get_value("Bench App", {"parent": destination.name, "app": "frappe"}, "release")
		frappe.db.set_value(
			"App Release",
			release,
			"creation",
			frappe.utils.add_days(frappe.utils.now_datetime(), -frappe_released_days_ago),
		)
		create_test_site_update(site.name, group, "Success", ignore_validate=True)
		frappe.db.set_value("Site", site.name, "bench", destination.name)

	def create_site_with_frappe_released_days_ago(self, days: int, clear_commit_time: bool = False):
		group = create_test_release_group([create_test_app()], frappe_version="Version 15")
		bench = create_test_bench(group=group)
		site = create_test_site(bench=bench.name)
		release = frappe.db.get_value("Bench App", {"parent": bench.name, "app": "frappe"}, "release")
		released_at = frappe.utils.add_days(frappe.utils.now_datetime(), -days)
		frappe.db.set_value("App Release", release, "timestamp", None if clear_commit_time else released_at)
		frappe.db.set_value("App Release", release, "creation", released_at)
		return Site("Site", site.name)

	def bands_for(self, counts: list[dict], site: Site) -> set[int]:
		"""Every band the site's version appears in.

		Other sites in the database share the version, so the test asserts that
		the expected band is present rather than that it is the only one.
		"""
		version = frappe.db.get_value("Release Group", site.group, "version")
		bands = {row.days_since_update for row in counts if row.frappe_version == version}
		self.assertTrue(bands, f"no audit row for {version}")
		return bands
