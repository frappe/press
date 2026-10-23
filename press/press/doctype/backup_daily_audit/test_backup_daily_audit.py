# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.backup_daily_audit.backup_daily_audit import record_backup_daily_audit
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_activity.site_activity import log_site_activity
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup
from press.press.doctype.site_plan.test_site_plan import create_test_plan

if TYPE_CHECKING:
	from press.press.doctype.backup_daily_audit.backup_daily_audit import BackupDailyAudit
	from press.press.doctype.site.site import Site


def create_test_backup_job(site: Site, status: str, hours_ago: float = 0, job_type: str = "Backup Site"):
	"""Backup agent job inserted straight into the db, so no steps or HTTP request get queued."""
	creation = frappe.utils.add_to_date(None, hours=-hours_ago)
	frappe.get_doc(
		{
			"doctype": "Agent Job",
			"job_type": job_type,
			"status": status,
			"site": site.name,
			"bench": site.bench,
			"server": site.server,
			"server_type": "Server",
			"request_method": "POST",
			"request_path": f"benches/{site.bench}/sites/{site.name}/backup",
			"request_data": "{}",
			"creation": creation,
			"modified": creation,
		}
	).db_insert()


class TestBackupDailyAudit(FrappeTestCase):
	def setUp(self):
		plan = create_test_plan("Site", price_usd=25.0)
		# Sites created within a window are not due a successful backup in it yet
		self.new_site = create_test_site(subdomain="newbackupsite", plan=plan.name)
		self.two_day_old_site = create_test_site(
			subdomain="twodaybackupsite", plan=plan.name, creation=frappe.utils.add_days(None, -2)
		)
		self.idle_site = create_test_site(
			subdomain="nobackupsuccess", plan=plan.name, creation=frappe.utils.add_days(None, -4)
		)

	def tearDown(self):
		frappe.db.rollback()

	def _create_backups(self, site: str, count: int, status: str = "Failure", hours_ago: float = 0):
		creation = frappe.utils.add_to_date(None, hours=-hours_ago)
		for _ in range(count):
			create_test_site_backup(site=site, status=status, creation=creation, offsite=False)

	def _record_audit(self) -> BackupDailyAudit:
		record_backup_daily_audit()
		return frappe.get_last_doc("Backup Daily Audit")

	def _listed_sites(self) -> tuple[list[str], list[str]]:
		audit = self._record_audit()
		return (
			[row.site for row in audit.sites_without_success_in_day],
			[row.site for row in audit.sites_without_success_in_3_days],
		)

	def test_audit_is_recorded_for_today(self):
		self.assertEqual(str(self._record_audit().audit_date), frappe.utils.today())

	def test_success_rate_counts_finished_backup_jobs_from_the_last_day(self):
		before = self._record_audit()
		for status in ("Success", "Success", "Success", "Failure", "Delivery Failure"):
			create_test_backup_job(self.idle_site, status)
		create_test_backup_job(self.idle_site, "Running")
		create_test_backup_job(self.idle_site, "Success", hours_ago=25)
		create_test_backup_job(self.idle_site, "Failure", job_type="Add Domain")

		audit = self._record_audit()

		self.assertEqual(audit.successful_jobs - before.successful_jobs, 3)
		self.assertEqual(audit.failed_jobs - before.failed_jobs, 2)
		finished_jobs = audit.successful_jobs + audit.failed_jobs
		self.assertAlmostEqual(audit.success_rate, audit.successful_jobs / finished_jobs * 100, places=2)

	def test_site_with_no_successful_backup_is_listed_with_failures_and_last_successful_backup(self):
		self._create_backups(self.idle_site.name, 1, status="Success", hours_ago=4 * 24)
		self._create_backups(self.idle_site.name, 2)

		audit = self._record_audit()

		for table in ("sites_without_success_in_day", "sites_without_success_in_3_days"):
			with self.subTest(table=table):
				row = next(row for row in audit.get(table) if row.site == self.idle_site.name)
				self.assertEqual(row.server, self.idle_site.server)
				self.assertEqual(row.team, self.idle_site.team)
				self.assertEqual(row.failed_backups, 2)
				self.assertIsNotNone(row.last_successful_backup)
		self.assertEqual(audit.sites_without_success_in_day_count, len(audit.sites_without_success_in_day))
		self.assertEqual(
			audit.sites_without_success_in_3_days_count, len(audit.sites_without_success_in_3_days)
		)

	def test_site_with_a_successful_backup_in_the_last_day_is_not_listed(self):
		self._create_backups(self.idle_site.name, 3)
		self._create_backups(self.idle_site.name, 1, status="Success")

		in_day, in_3_days = self._listed_sites()

		self.assertNotIn(self.idle_site.name, in_day)
		self.assertNotIn(self.idle_site.name, in_3_days)

	def test_site_with_a_successful_backup_two_days_ago_is_listed_for_the_last_day_only(self):
		self._create_backups(self.idle_site.name, 1, status="Success", hours_ago=2 * 24)

		in_day, in_3_days = self._listed_sites()

		self.assertIn(self.idle_site.name, in_day)
		self.assertNotIn(self.idle_site.name, in_3_days)

	def test_pending_and_running_backups_are_not_a_success(self):
		self._create_backups(self.idle_site.name, 1, status="Pending", hours_ago=3)
		self._create_backups(self.idle_site.name, 1, status="Running", hours_ago=3)

		in_day, _ = self._listed_sites()

		self.assertIn(self.idle_site.name, in_day)

	def test_physical_backup_success_counts(self):
		self._create_backups(self.idle_site.name, 1, status="Success")
		frappe.db.set_value("Site Backup", {"site": self.idle_site.name}, "physical", True)

		in_day, in_3_days = self._listed_sites()

		self.assertNotIn(self.idle_site.name, in_day)
		self.assertNotIn(self.idle_site.name, in_3_days)

	def test_site_with_only_physical_backups_scheduled_is_listed(self):
		frappe.db.set_value(
			"Site",
			self.idle_site.name,
			{"skip_scheduled_logical_backups": True, "skip_scheduled_physical_backups": False},
		)

		in_day, _ = self._listed_sites()

		self.assertIn(self.idle_site.name, in_day)

	def test_failed_backups_are_counted_within_each_window(self):
		self._create_backups(self.idle_site.name, 1, hours_ago=25)

		audit = self._record_audit()

		in_day = {row.site: row.failed_backups for row in audit.sites_without_success_in_day}
		in_3_days = {row.site: row.failed_backups for row in audit.sites_without_success_in_3_days}
		self.assertEqual(in_day[self.idle_site.name], 0)
		self.assertEqual(in_3_days[self.idle_site.name], 1)

	def test_sites_are_listed_only_for_windows_they_existed_through(self):
		in_day, in_3_days = self._listed_sites()

		self.assertNotIn(self.new_site.name, in_day)
		self.assertIn(self.two_day_old_site.name, in_day)
		self.assertNotIn(self.two_day_old_site.name, in_3_days)

	def test_site_activated_within_the_window_is_not_listed(self):
		log_site_activity(self.idle_site.name, "Activate Site")

		in_day, in_3_days = self._listed_sites()

		self.assertNotIn(self.idle_site.name, in_day)
		self.assertNotIn(self.idle_site.name, in_3_days)

	def test_site_on_server_with_scheduled_backups_skipped_is_not_listed(self):
		frappe.db.set_value("Server", self.idle_site.server, "skip_scheduled_backups", True)

		in_day, in_3_days = self._listed_sites()

		self.assertNotIn(self.idle_site.name, in_day)
		self.assertNotIn(self.idle_site.name, in_3_days)

	def test_site_with_frequent_failures_is_listed_even_after_a_success(self):
		self._create_backups(self.idle_site.name, 3)
		self._create_backups(self.idle_site.name, 1, status="Success")

		audit = self._record_audit()

		row = next(row for row in audit.sites_with_frequent_failures if row.site == self.idle_site.name)
		self.assertEqual(row.failed_backups, 3)
		self.assertIsNotNone(row.last_successful_backup)
		self.assertEqual(audit.sites_with_frequent_failures_count, len(audit.sites_with_frequent_failures))

	def test_failures_under_the_threshold_or_older_than_a_day_are_not_frequent(self):
		self._create_backups(self.idle_site.name, 2)
		self._create_backups(self.two_day_old_site.name, 3, hours_ago=25)

		listed = [row.site for row in self._record_audit().sites_with_frequent_failures]

		self.assertNotIn(self.idle_site.name, listed)
		self.assertNotIn(self.two_day_old_site.name, listed)

	def test_site_with_all_scheduled_backups_skipped_is_not_listed(self):
		frappe.db.set_value(
			"Site",
			self.idle_site.name,
			{"skip_scheduled_logical_backups": True, "skip_scheduled_physical_backups": True},
		)

		in_day, in_3_days = self._listed_sites()

		self.assertNotIn(self.idle_site.name, in_day)
		self.assertNotIn(self.idle_site.name, in_3_days)
