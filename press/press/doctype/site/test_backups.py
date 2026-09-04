from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.backups import (
	FIFO,
	GFS,
	ScheduledBackupJob,
	schedule_logical_backups_for_sites_with_backup_time,
	schedule_physical_backups_for_sites_with_backup_time,
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
		super().setUp()

		self.interval = 6
		frappe.db.set_single_value("Press Settings", "backup_interval", 6)

	def _interval_hrs_ago(self):
		return frappe.utils.now_datetime() - timedelta(hours=self.interval)

	def _create_site_requiring_backup(self, **kwargs):
		return create_test_site(creation=self._interval_hrs_ago() - timedelta(hours=1), **kwargs)

	@patch.object(
		ScheduledBackupJob,
		"is_backup_hour",
		new=lambda self, x: True,  # always backup hour
	)
	@patch.object(
		ScheduledBackupJob,
		"take_offsite",
		new=lambda self, x, y: True,  # take offsite anyway
	)
	def test_offsite_taken_once_per_day(self):
		site = self._create_site_requiring_backup()
		job = ScheduledBackupJob(backup_type="Logical")

		offsite_count_before = self._offsite_count(site.name)
		job.start()
		frappe.get_last_doc("Site Backup", dict(site=site.name)).db_set("status", "Success")
		offsite_count_after = self._offsite_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before + 1)

		offsite_count_before = self._offsite_count(site.name)
		job = ScheduledBackupJob(backup_type="Logical")
		job.start()
		offsite_count_after = self._offsite_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	@patch.object(
		ScheduledBackupJob,
		"is_backup_hour",
		new=lambda self, x: True,  # always backup hour
	)
	def test_with_files_taken_once_per_day(self):
		site = self._create_site_requiring_backup()
		job = ScheduledBackupJob(backup_type="Logical")

		offsite_count_before = self._with_files_count(site.name)
		job.start()
		frappe.get_last_doc("Site Backup", dict(site=site.name)).db_set("status", "Success")
		offsite_count_after = self._with_files_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before + 1)

		offsite_count_before = self._with_files_count(site.name)
		job = ScheduledBackupJob(backup_type="Logical")
		job.start()
		offsite_count_after = self._with_files_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	def _create_x_sites_on_1_bench(self, x):
		site = self._create_site_requiring_backup()
		bench = site.bench
		for _i in range(x - 1):
			self._create_site_requiring_backup(bench=bench)

	def test_limit_number_of_sites_backed_up(self):
		self._create_x_sites_on_1_bench(1)
		self._create_x_sites_on_1_bench(2)
		limit = 3

		job = ScheduledBackupJob(backup_type="Logical")
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

		job = ScheduledBackupJob(backup_type="Logical")
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
	def test_site_with_logical_backup_time_taken_at_right_time(self, mock_backup):
		site: Site = self._create_site_requiring_backup()
		site.schedule_logical_backup_at_custom_time = True
		site.append(
			"logical_backup_times",
			{
				"backup_time": "00:00",
			},
		)
		site.save()
		with self.freeze_time("2021-01-01 01:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()
		with self.freeze_time("2021-01-01 00:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		job = ScheduledBackupJob(backup_type="Logical")
		self.assertEqual(len(job.sites), 0)  # site with backup time should be skipped

	@patch.object(Site, "backup")
	def test_site_with_physical_backup_time_taken_at_right_time(self, mock_backup):
		site: Site = self._create_site_requiring_backup()
		site.skip_scheduled_physical_backups = False
		site.schedule_physical_backup_at_custom_time = True
		site.append(
			"physical_backup_times",
			{
				"backup_time": "00:00:00",
			},
		)
		site.save()
		with self.freeze_time("2021-01-01 01:00"):
			schedule_physical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()
		with self.freeze_time("2021-01-01 00:00"):
			schedule_physical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		print(mock_backup.call_args)
		job = ScheduledBackupJob(backup_type="Physical")
		self.assertEqual(len(job.sites), 0)  # site with backup time should be skipped

	@patch.object(Site, "backup")
	def test_site_with_multiple_logical_backup_times(self, mock_backup):
		site: Site = self._create_site_requiring_backup()
		site.schedule_logical_backup_at_custom_time = True
		site.append(
			"logical_backup_times",
			{
				"backup_time": "01:00:00",
			},
		)
		site.append(
			"logical_backup_times",
			{
				"backup_time": "05:00:00",
			},
		)
		site.append(
			"logical_backup_times",
			{
				"backup_time": "12:00:00",
			},
		)
		site.save()
		with self.freeze_time("2021-01-01 00:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 01:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		mock_backup.reset_mock()

		with self.freeze_time("2021-01-01 02:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 03:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 04:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 05:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		mock_backup.reset_mock()

		with self.freeze_time("2021-01-01 06:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_not_called()

		with self.freeze_time("2021-01-01 12:00"):
			schedule_logical_backups_for_sites_with_backup_time()
		mock_backup.assert_called_once()
		mock_backup.reset_mock()


class TestBackupExpiry(FrappeTestCase):
	"""What retention leaves behind, which is all an audit has to go on later."""

	def setUp(self):
		super().setUp()
		self.site = create_test_site(subdomain="expiring")

	def tearDown(self):
		frappe.db.rollback()

	def expire(self, backup, scheme=None):
		(scheme or GFS()).cleanup_offsite()
		return frappe.db.get_value(
			"Site Backup",
			backup.name,
			["files_availability", "files_expired_on", "retention_rule"],
			as_dict=True,
		)

	def test_expiry_records_when_the_files_were_deleted(self):
		backup = create_test_site_backup(self.site.name, creation=frappe.utils.add_days(None, -30))

		with patch("press.press.doctype.site.backups.delete_remote_backup_objects"):
			expired = self.expire(backup)

		self.assertEqual(expired.files_availability, "Unavailable")
		self.assertIsNotNone(expired.files_expired_on)

	def test_expiry_names_the_tier_that_was_holding_the_backup(self):
		# A Wednesday, so no weekly, monthly or yearly copy is keeping it
		backup = create_test_site_backup(self.site.name, creation=getdate("2026-02-11"))

		with patch("press.press.doctype.site.backups.delete_remote_backup_objects"):
			expired = self.expire(backup)

		self.assertEqual(expired.retention_rule, "Daily")

	def test_a_sunday_is_expired_as_the_weekly_copy(self):
		self.assertEqual(GFS().rule_for(getdate("2026-02-15")), "Weekly")

	def test_the_first_of_a_month_is_expired_as_the_monthly_copy(self):
		self.assertEqual(GFS().rule_for(getdate("2026-02-01")), "Monthly")

	def test_new_years_day_is_expired_as_the_yearly_copy(self):
		self.assertEqual(GFS().rule_for(getdate("2026-01-01")), "Yearly")

	def test_a_daily_copy_is_kept_for_a_week(self):
		self.assertEqual(GFS().keep_till(getdate("2026-02-11")), getdate("2026-02-18"))

	def test_a_monthly_copy_is_kept_for_a_year(self):
		self.assertEqual(GFS().keep_till(getdate("2026-02-01")), getdate("2027-02-02"))

	def test_a_scheme_without_fixed_windows_promises_no_date(self):
		self.assertIsNone(FIFO().keep_till(getdate("2026-02-11")))
