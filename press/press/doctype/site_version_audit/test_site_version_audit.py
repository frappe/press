# Copyright (c) 2026, Frappe and Contributors
# See license.txt
from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.app.test_app import create_test_app
from press.press.doctype.app_release.test_app_release import create_test_app_release
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

	def test_audit_for_a_past_date_ignores_an_in_place_update_made_since(self):
		"""An in place update rewrites Bench App, so a past date must not read it."""
		site = self.create_site_with_frappe_released_days_ago(400)
		self.backdate_site(site, days=60)
		self.update_bench_in_place(site)

		month_end = frappe.utils.add_days(frappe.utils.today(), -30)

		self.assertIn(0, self.bands_for(count_sites_by_version_and_age(), site))
		self.assertIn(360, self.bands_for(count_sites_by_version_and_age_on(month_end), site))

	def test_audit_for_a_past_date_uses_the_bench_a_move_had_not_yet_left(self):
		"""A move created before the date but completed after had not happened yet."""
		site = self.create_site_with_frappe_released_days_ago(400)
		self.backdate_site(site, days=60)
		month_end = frappe.utils.add_days(frappe.utils.today(), -30)
		self.move_site_to_a_fresh_bench(
			site,
			frappe_released_days_ago=3,
			created_on=frappe.utils.add_days(month_end, -5),
			completed_on=frappe.utils.add_days(month_end, 5),
		)

		bands = self.bands_for(count_sites_by_version_and_age_on(month_end), site)

		self.assertIn(360, bands)

	def test_audit_counts_a_site_once_when_two_moves_share_a_completion_time(self):
		"""Nothing stops two moves sharing update_end, and a tie must not double count."""
		site = self.create_site_with_frappe_released_days_ago(400)
		self.backdate_site(site, days=60)
		month_end = frappe.utils.add_days(frappe.utils.today(), -30)
		completed_on = frappe.utils.add_days(month_end, 5)
		self.move_site_to_a_fresh_bench(site, 3, completed_on=completed_on)
		before = sum(row.sites for row in count_sites_by_version_and_age_on(month_end))

		self.move_site_to_a_fresh_bench(site, 3, completed_on=completed_on)

		after = sum(row.sites for row in count_sites_by_version_and_age_on(month_end))
		self.assertEqual(before, after)

	def test_audit_takes_the_bench_and_group_of_one_move_when_two_are_tied(self):
		"""Tied moves must not have their bench taken from one and group from another."""
		old_bench, new_bench = self.two_benches_on_their_own_versions()
		site = create_test_site(bench=old_bench.name)
		self.backdate_site(Site("Site", site.name), days=60)
		month_end = frappe.utils.add_days(frappe.utils.today(), -30)

		# cross the orderings, so an aggregate per field draws from both rows
		benches = sorted([old_bench.name, new_bench.name])
		groups = sorted([old_bench.group, new_bench.group])
		self.tied_move(site.name, benches[0], groups[1], month_end)
		self.tied_move(site.name, benches[1], groups[0], month_end)

		bands = {b.name: 360 if b is old_bench else 0 for b in (old_bench, new_bench)}
		versions = {
			b.group: frappe.db.get_value("Release Group", b.group, "version") for b in (old_bench, new_bench)
		}
		valid = {(versions[groups[1]], bands[benches[0]]), (versions[groups[0]], bands[benches[1]])}
		observed = {
			(row.frappe_version, row.days_since_update)
			for row in count_sites_by_version_and_age_on(month_end)
			if row.frappe_version in versions.values()
		}

		self.assertEqual(len(observed), 1)
		self.assertTrue(observed <= valid, f"{observed} is not one of {valid}")

	def test_audit_ignores_a_failed_move_tied_with_the_completed_one(self):
		"""A move that never completed must not win the tie break."""
		old_bench, new_bench = self.two_benches_on_their_own_versions()
		site = create_test_site(bench=old_bench.name)
		self.backdate_site(Site("Site", site.name), days=60)
		month_end = frappe.utils.add_days(frappe.utils.today(), -30)

		moves = [
			self.tied_move(site.name, new_bench.name, new_bench.group, month_end),
			self.tied_move(site.name, old_bench.name, old_bench.group, month_end),
		]
		# the move to ignore has to sort first, or the tie break hides the bug
		ignored, kept = sorted(moves)
		frappe.db.set_value(
			"Site Update",
			ignored,
			{"status": "Failure", "source_bench": new_bench.name, "group": new_bench.group},
		)
		frappe.db.set_value(
			"Site Update",
			kept,
			{"status": "Success", "source_bench": old_bench.name, "group": old_bench.group},
		)

		version = frappe.db.get_value("Release Group", old_bench.group, "version")
		observed = {
			(row.frappe_version, row.days_since_update)
			for row in count_sites_by_version_and_age_on(month_end)
			if row.frappe_version.startswith("Version 9")
		}

		self.assertEqual(observed, {(version, 360)})

	def test_audit_takes_the_first_of_two_moves_that_share_a_completion_time(self):
		"""Two moves in a chain: the site sat on the first one's source, not the second's."""
		left_bench, intermediate = self.two_benches_on_their_own_versions()
		site = create_test_site(bench=left_bench.name)
		self.backdate_site(Site("Site", site.name), days=60)
		month_end = frappe.utils.add_days(frappe.utils.today(), -30)

		moves = [
			self.tied_move(site.name, left_bench.name, left_bench.group, month_end),
			self.tied_move(site.name, intermediate.name, intermediate.group, month_end),
		]
		# the later move has to sort first by name, or name ordering hides the bug
		later, earlier = sorted(moves)
		self.place_move(earlier, left_bench, created_on=frappe.utils.add_days(month_end, -10))
		self.place_move(later, intermediate, created_on=frappe.utils.add_days(month_end, -5))

		version = frappe.db.get_value("Release Group", left_bench.group, "version")
		observed = {
			(row.frappe_version, row.days_since_update)
			for row in count_sites_by_version_and_age_on(month_end)
			if row.frappe_version.startswith("Version 9")
		}

		self.assertEqual(observed, {(version, 360)})

	def test_audit_ignores_a_legacy_move_that_completed_before_the_date(self):
		"""A row with no update_end whose modified drifted past its completion."""
		old_bench, new_bench = self.two_benches_on_their_own_versions()
		site = create_test_site(bench=new_bench.name)
		self.backdate_site(Site("Site", site.name), days=60)
		month_end = frappe.utils.add_days(frappe.utils.today(), -30)

		move = self.tied_move(site.name, old_bench.name, old_bench.group, month_end)
		frappe.db.set_value(
			"Site Update",
			move,
			{
				"update_end": None,
				"update_start": frappe.utils.add_days(month_end, -5),
				"modified": frappe.utils.add_days(month_end, 5),
			},
			update_modified=False,
		)

		# the move finished before the date, so the site had already left old_bench
		version = frappe.db.get_value("Release Group", new_bench.group, "version")
		observed = {
			(row.frappe_version, row.days_since_update)
			for row in count_sites_by_version_and_age_on(month_end)
			if row.frappe_version.startswith("Version 9")
		}

		self.assertEqual(observed, {(version, 0)})

	def place_move(self, move: str, bench, created_on):
		frappe.db.set_value(
			"Site Update",
			move,
			{"source_bench": bench.name, "group": bench.group, "creation": created_on},
		)

	def two_benches_on_their_own_versions(self):
		"""Benches on versions no other site uses, so the counts stay isolated."""
		benches = []
		for number, released_days_ago in ((98, 400), (99, 3)):
			frappe.get_doc(
				doctype="Frappe Version", name=f"Version {number}", number=number, status="Stable"
			).insert(ignore_if_duplicate=True)
			group = create_test_release_group([create_test_app()], frappe_version=f"Version {number}")
			bench = create_test_bench(group=group)
			self.age_the_built_release(bench, released_days_ago)
			benches.append(bench)

		self.assertNotEqual(
			self.built_release(benches[0]),
			self.built_release(benches[1]),
			"the two benches must not share a release, or ageing one ages both",
		)
		return benches

	def built_release(self, bench) -> str:
		"""The frappe release the audit reads for a past date, via the candidate."""
		candidate = frappe.db.get_value("Bench", bench.name, "candidate")
		app = frappe.db.get_value(
			"Deploy Candidate App",
			{"parent": candidate, "app": "frappe"},
			["pullable_release", "release"],
			as_dict=True,
		)
		return app.pullable_release or app.release

	def age_the_built_release(self, bench, days: int):
		"""The age is read from `timestamp` first, so both fields have to move."""
		released_at = frappe.utils.add_days(frappe.utils.now_datetime(), -days)
		frappe.db.set_value(
			"App Release", self.built_release(bench), {"timestamp": released_at, "creation": released_at}
		)

	def tied_move(self, site: str, source_bench: str, group: str, month_end: str) -> str:
		"""A completed move sharing its completion time with the others."""
		update = create_test_site_update(site, group, "Success", ignore_validate=True)
		frappe.db.set_value(
			"Site Update",
			update.name,
			{
				"source_bench": source_bench,
				"group": group,
				"update_end": frappe.utils.add_days(month_end, 5),
			},
		)
		return update.name

	def backdate_site(self, site: Site, days: int):
		"""The audit skips a site that did not exist yet on the date asked about."""
		frappe.db.set_value(
			"Site", site.name, "creation", frappe.utils.add_days(frappe.utils.now_datetime(), -days)
		)

	def update_bench_in_place(self, site: Site):
		"""Point Bench App at a release built today, leaving the candidate alone."""
		bench_app = {"parent": site.bench, "app": "frappe"}
		source = frappe.db.get_value("Bench App", bench_app, "source")
		fresh = create_test_app_release(frappe.get_doc("App Source", source))
		frappe.db.set_value("Bench App", bench_app, "release", fresh.name)

	def move_site_to_a_fresh_bench(
		self,
		site: Site,
		frappe_released_days_ago: int,
		created_on=None,
		completed_on=None,
	):
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
		update = create_test_site_update(site.name, group, "Success", ignore_validate=True)
		if created_on:
			frappe.db.set_value("Site Update", update.name, "creation", created_on)
		frappe.db.set_value(
			"Site Update", update.name, "update_end", completed_on or frappe.utils.now_datetime()
		)
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
