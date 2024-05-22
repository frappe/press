from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

from frappe.tests.utils import FrappeTestCase
import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.backups import (
	ScheduledBackupJob,
	schedule_for_sites_with_backup_time,
)
from press.press.doctype.site.site import Site
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup


@patch("press.press.doctype.site.backups.frappe.db.commit", new=MagicMock)
@patch("press.press.doctype.site.backups.frappe.db.rollback", new=MagicMock)
@patch.object(AgentJob, "after_insert", new=Mock())
class TestScheduledBackupJob(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _offsite_count(self, site: str):
		return frappe.db.count("Site Backup", {"site": site, "offsite": True})

	def _with_files_count(self, site: str):
		return frappe.db.count("Site Backup", {"site": site, "with_files": True})

	def setUp(self):
		self.interval = 6
		frappe.db.set_single_value("Press Settings", "backup_interval", 6)

	def _interval_hrs_ago(self):
		return frappe.utils.now_datetime() - timedelta(hours=self.interval)

	def _create_site_requiring_backup(self, **kwargs):
		return create_test_site(
			creation=self._interval_hrs_ago() - timedelta(hours=1), **kwargs
		)

	@patch.object(
		ScheduledBackupJob, "is_backup_hour", new=lambda self, x: True  # always backup hour
	)
	@patch.object(
		ScheduledBackupJob,
		"take_offsite",
		new=lambda self, x, y: True,  # take offsite anyway
	)
	def test_offsite_taken_once_per_day(self):
		site = self._create_site_requiring_backup()
		job = ScheduledBackupJob()

		offsite_count_before = self._offsite_count(site.name)
		job.start()
		frappe.get_last_doc("Site Backup", dict(site=site.name)).db_set("status", "Success")
		offsite_count_after = self._offsite_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before + 1)

		offsite_count_before = self._offsite_count(site.name)
		job = ScheduledBackupJob()
		job.start()
		offsite_count_after = self._offsite_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	@patch.object(
		ScheduledBackupJob, "is_backup_hour", new=lambda self, x: True  # always backup hour
	)
	def test_with_files_taken_once_per_day(self):
		site = self._create_site_requiring_backup()
		job = ScheduledBackupJob()

		offsite_count_before = self._with_files_count(site.name)
		job.start()
		frappe.get_last_doc("Site Backup", dict(site=site.name)).db_set("status", "Success")
		offsite_count_after = self._with_files_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before + 1)

		offsite_count_before = self._with_files_count(site.name)
		job = ScheduledBackupJob()
		job.start()
		offsite_count_after = self._with_files_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	def _create_x_sites_on_1_bench(self, x):
		site = self._create_site_requiring_backup()
		bench = site.bench
		for i in range(x - 1):
			self._create_site_requiring_backup(bench=bench)

	def test_limit_number_of_sites_backed_up(self):
		self._create_x_sites_on_1_bench(1)
		self._create_x_sites_on_1_bench(2)
		limit = 3

		job = ScheduledBackupJob()
		sites_num_old = len(job.sites)

		job.limit = limit
		job.start()
		sites_for_backup = [site.name for site in job.sites]
		frappe.db.set_value(
			"Site Backup",
			{"site": ("in", sites_for_backup)},
			"status",
			"Success",  # fake succesful backup
		)

		job = ScheduledBackupJob()
		sites_num_new = len(job.sites)

		self.assertLess(sites_num_new, sites_num_old)
		self.assertEqual(sites_num_old - sites_num_new, limit)

	def test_sites_considered_for_backup(self):
		"""Ensure sites with succesful or pending backups in past interval are skipped."""
		sites = Site.get_sites_for_backup(self.interval)
		self.assertEqual(sites, [])

		site_1 = self._create_site_requiring_backup()
		create_test_site_backup(site_1.name, status="Pending")
		site_2 = self._create_site_requiring_backup()
		create_test_site_backup(site_2.name, status="Failure")
		site_3 = self._create_site_requiring_backup()
		create_test_site_backup(site_3.name, status="Success")
		site_4 = self._create_site_requiring_backup()
		create_test_site_backup(site_4.name, status="Running")

		sites = Site.get_sites_for_backup(self.interval)
		self.assertEqual(len(sites), 1)

		sites_for_backup = [site.name for site in sites]
		self.assertIn(site_2.name, sites_for_backup)

	@patch.object(Site, "backup")
	def test_site_with_backup_time_taken_at_right_time(self, mock_backup):
		self._create_site_requiring_backup(backup_time="00:00:00")
		with self.freeze_time("2021-01-01 01:00"):
			schedule_for_sites_with_backup_time()
		mock_backup.assert_not_called()
		with self.freeze_time("2021-01-01 00:00"):
			schedule_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		job = ScheduledBackupJob()
		self.assertEqual(len(job.sites), 0)  # site with backup time should be skipped
