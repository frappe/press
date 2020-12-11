import unittest
from datetime import date, timedelta
from unittest.mock import Mock, patch

import frappe

from press.press.cleanup import GFS, cleanup_backups
from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_backup.test_site_backup import create_test_site_backup


@patch.object(AgentJob, "after_insert", new=Mock())
class TestGFS(unittest.TestCase):
	"""Test Grandfather-father-son policy for keeping backups."""

	def tearDown(self):
		frappe.db.rollback()

	def test_only_daily_backups_longer_than_limit_deleted(self):
		"""Ensure only daily backups kept for longer than limit are deleted."""
		site = create_test_site("testsubdomain")
		oldest_allowed_daily = date.today() - timedelta(days=GFS.daily)
		older_than_oldest_allowed_daily = oldest_allowed_daily - timedelta(days=1)
		newer_than_oldest_allowed_daily = oldest_allowed_daily + timedelta(days=1)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_daily)
		older_backup = create_test_site_backup(site.name, older_than_oldest_allowed_daily)
		newer_backup = create_test_site_backup(site.name, newer_than_oldest_allowed_daily)

		gfs = GFS()
		gfs.expire_offsite_backups(site)

		limit_backup.reload()
		older_backup.reload()
		newer_backup.reload()

		self.assertEqual(limit_backup.files_availability, "Available")
		self.assertEqual(older_backup.files_availability, "Unavailable")
		self.assertEqual(newer_backup.files_availability, "Available")

	def _get_next_weekly_backup_day(self, day: date) -> date:
		backup_day = (GFS.weekly_backup_day + 5) % 7
		return day + timedelta(backup_day - day.weekday())

	def _get_previous_weekly_backup_day(self, day: date) -> date:
		backup_day = (GFS.weekly_backup_day + 5) % 7
		return day - timedelta(7 - (backup_day - day.weekday()))

	def test_only_weekly_backups_longer_than_limit_deleted(self):
		"""Ensure only weekly backups kept for longer than limit are deleted."""
		site = create_test_site("testsubdomain")
		weekly_backup_day = (
			GFS.weekly_backup_day + 5
		) % 7  # convert from sql to python for day of week standard
		a_month_ago = date.today() - timedelta(weeks=4)
		oldest_allowed_weekly = (
			a_month_ago
			if a_month_ago.weekday() == weekly_backup_day
			else self._get_next_weekly_backup_day(a_month_ago)
		)
		older_than_oldest_allowed_weekly = self._get_previous_weekly_backup_day(
			oldest_allowed_weekly
		)
		newer_than_oldest_allowed_weekly = self._get_next_weekly_backup_day(
			oldest_allowed_weekly
		)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_weekly)
		older_backup = create_test_site_backup(site.name, older_than_oldest_allowed_weekly)
		newer_backup = create_test_site_backup(site.name, newer_than_oldest_allowed_weekly)

		gfs = GFS()
		gfs.expire_offsite_backups(site)

		limit_backup.reload()
		older_backup.reload()
		newer_backup.reload()

		self.assertEqual(limit_backup.files_availability, "Available")
		self.assertEqual(older_backup.files_availability, "Unavailable")
		self.assertEqual(newer_backup.files_availability, "Available")

	def _get_next_monthly_backup_day(self, day: date):
		backup_day = GFS.monthly_backup_day
		return (day.replace(day=1) + timedelta(days=32)).replace(day=backup_day)

	def _get_previous_monthly_backup_day(self, day: date):
		backup_day = GFS.monthly_backup_day
		return (day.replace(day=1) - timedelta(days=1)).replace(day=backup_day)

	def test_only_monthly_backups_longer_than_limit_deleted(self):
		"""Ensure only monthly backups kept for longer than limit are deleted."""
		site = create_test_site("testsubdomain")
		a_year_ago = date.today() - timedelta(days=366)
		oldest_allowed_monthly = (
			a_year_ago
			if a_year_ago.day == GFS.monthly_backup_day
			else self._get_next_monthly_backup_day(a_year_ago)
		)
		older_than_oldest_allowed_monthly = self._get_previous_monthly_backup_day(
			oldest_allowed_monthly
		)
		newer_than_oldest_allowed_monthly = self._get_next_monthly_backup_day(
			oldest_allowed_monthly
		)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_monthly)
		older_backup = create_test_site_backup(site.name, older_than_oldest_allowed_monthly)
		newer_backup = create_test_site_backup(site.name, newer_than_oldest_allowed_monthly)

		gfs = GFS()
		gfs.expire_offsite_backups(site)

		limit_backup.reload()
		older_backup.reload()
		newer_backup.reload()

		self.assertEqual(limit_backup.files_availability, "Available")
		self.assertEqual(older_backup.files_availability, "Unavailable")
		self.assertEqual(newer_backup.files_availability, "Available")

	def _get_next_yearly_backup_day(self, day: date) -> date:
		backup_day = GFS.yearly_backup_day
		next_new_year = day.replace(year=day.year + 1).replace(month=1).replace(day=1)
		return next_new_year + timedelta(backup_day - 1)

	def _get_previous_yearly_backup_day(self, day: date) -> date:
		backup_day = GFS.yearly_backup_day
		prev_new_year = day.replace(year=day.year - 1).replace(month=1).replace(day=1)
		return prev_new_year + timedelta(backup_day - 1)

	def test_only_yearly_backups_older_than_limit_deleted(self):
		"""Ensure only yearly backups kept for longer than limit are deleted."""
		site = create_test_site("testsubdomain")
		_10_years_ago = date.today() - timedelta(3653)
		oldest_allowed_yearly = (
			_10_years_ago
			if _10_years_ago.day == GFS.yearly_backup_day
			else self._get_next_yearly_backup_day(_10_years_ago)
		)
		older_than_oldest_allowed_yearly = self._get_previous_yearly_backup_day(
			oldest_allowed_yearly
		)
		newer_than_oldest_allowed_yearly = self._get_next_yearly_backup_day(
			oldest_allowed_yearly
		)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_yearly)
		older_backup = create_test_site_backup(site.name, older_than_oldest_allowed_yearly)
		newer_backup = create_test_site_backup(site.name, newer_than_oldest_allowed_yearly)

		gfs = GFS()
		gfs.expire_offsite_backups(site)

		limit_backup.reload()
		older_backup.reload()
		newer_backup.reload()

		self.assertEqual(limit_backup.files_availability, "Available")
		self.assertEqual(older_backup.files_availability, "Unavailable")
		self.assertEqual(newer_backup.files_availability, "Available")
