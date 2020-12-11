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

	def _get_next_sunday(self, day: date) -> date:
		weekday = day.weekday()
		sunday = 6  # weekday() returns 0-6 for mon-sun
		next_sunday = day + timedelta(sunday - weekday)
		if next_sunday == day:
			next_sunday += timedelta(7)
		self.assertEqual(next_sunday.weekday(), sunday)
		return next_sunday

	def _get_previous_sunday(self, day: date) -> date:
		weekday = day.weekday()
		sunday = 6  # weekday() returns 0-6 for mon-sun
		prev_sunday = day - timedelta(7 - (sunday - weekday))
		if prev_sunday == day:
			prev_sunday -= timedelta(7)
		self.assertEqual(prev_sunday.weekday(), sunday)
		return prev_sunday

	def test_only_weekly_backups_longer_than_limit_deleted(self):
		"""
		Ensure only weekly backups kept for longer than limit are deleted.

		(Assuming 4 is limit for weekly backups and sundays are when weekly backups are taken.)
		"""
		site = create_test_site("testsubdomain")
		sunday = 6
		a_month_ago = date.today() - timedelta(weeks=4)
		oldest_allowed_weekly = (
			a_month_ago
			if a_month_ago.weekday() == sunday
			else self._get_next_sunday(a_month_ago)
		)
		older_than_oldest_allowed_weekly = self._get_previous_sunday(oldest_allowed_weekly)
		newer_than_oldest_allowed_weekly = self._get_next_sunday(oldest_allowed_weekly)

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
		"""
		Ensure only monthly backups kept for longer than limit are deleted.

		(Assuming 12 is limit for monthly backups and backups are taken on 1st of the month.)
		"""
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
