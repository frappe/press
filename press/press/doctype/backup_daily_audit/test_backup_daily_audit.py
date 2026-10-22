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
		frappe.db.set_single_value("Press Settings", "max_failed_backup_attempts_in_a_day", 3)
		plan = create_test_plan("Site", price_usd=25.0)
		# Sites created in the last 3 days are not due a successful backup yet
		self.site = create_test_site(subdomain="allbackupsfailed", plan=plan.name)
		self.other_site = create_test_site(subdomain="allbackupsfailed2", plan=plan.name)
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

	def _sites_without_success(self) -> list[str]:
		return [row.site for row in self._record_audit().sites_without_success]

	def test_audit_is_recorded_for_today(self):
		self.assertEqual(str(self._record_audit().audit_date), frappe.utils.today())

	def test_success_rate_counts_finished_backup_jobs_from_the_last_day(self):
		before = self._record_audit()
		for status in ("Success", "Success", "Success", "Failure", "Delivery Failure"):
			create_test_backup_job(self.site, status)
		create_test_backup_job(self.site, "Running")
		create_test_backup_job(self.site, "Success", hours_ago=25)
		create_test_backup_job(self.site, "Failure", job_type="Add Domain")

		audit = self._record_audit()

		self.assertEqual(audit.successful_jobs - before.successful_jobs, 3)
		self.assertEqual(audit.failed_jobs - before.failed_jobs, 2)
		finished_jobs = audit.successful_jobs + audit.failed_jobs
		self.assertAlmostEqual(audit.success_rate, audit.successful_jobs / finished_jobs * 100, places=2)

	def test_site_with_no_successful_backup_job_in_three_days_is_listed_with_last_successful_backup(self):
		create_test_backup_job(self.idle_site, "Success", hours_ago=4 * 24)
		create_test_backup_job(self.idle_site, "Failure")
		self._create_backups(self.idle_site.name, 1, status="Success", hours_ago=4 * 24)

		audit = self._record_audit()

		row = next(row for row in audit.sites_without_success if row.site == self.idle_site.name)
		self.assertEqual(row.server, self.idle_site.server)
		self.assertEqual(row.team, self.idle_site.team)
		self.assertIsNotNone(row.last_successful_backup)
		self.assertEqual(audit.sites_without_success_count, len(audit.sites_without_success))

	def test_site_with_a_successful_backup_job_in_three_days_is_not_listed(self):
		create_test_backup_job(self.idle_site, "Success", hours_ago=2 * 24)

		self.assertNotIn(self.idle_site.name, self._sites_without_success())

	def test_site_with_a_pending_or_running_backup_job_is_not_listed(self):
		for status in ("Pending", "Running"):
			with self.subTest(status=status):
				create_test_backup_job(self.idle_site, status)

				self.assertNotIn(self.idle_site.name, self._sites_without_success())
				frappe.db.delete("Agent Job", {"site": self.idle_site.name, "job_type": "Backup Site"})

	def test_site_created_within_three_days_is_not_listed(self):
		self.assertNotIn(self.site.name, self._sites_without_success())

	def test_site_activated_within_three_days_is_not_listed(self):
		log_site_activity(self.idle_site.name, "Activate Site")

		self.assertNotIn(self.idle_site.name, self._sites_without_success())

	def test_site_on_server_with_scheduled_backups_skipped_is_not_listed(self):
		frappe.db.set_value("Server", self.idle_site.server, "skip_scheduled_backups", True)

		self.assertNotIn(self.idle_site.name, self._sites_without_success())

	def test_sites_that_hit_the_failed_backup_limit_are_listed_with_their_failure_count(self):
		self._create_backups(self.site.name, 3)
		self._create_backups(self.other_site.name, 2)

		audit = self._record_audit()

		failures = {row.site: row.failed_backups for row in audit.failed_sites}
		self.assertEqual(failures.get(self.site.name), 3)
		self.assertNotIn(self.other_site.name, failures)
		self.assertEqual(audit.failed_site_count, len(audit.failed_sites))

	def test_failed_backups_older_than_a_day_are_not_counted(self):
		self._create_backups(self.site.name, 3, hours_ago=25)

		self.assertNotIn(self.site.name, [row.site for row in self._record_audit().failed_sites])
