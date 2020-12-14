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
	"""Test Grandfather-father-son rotation scheme of keeping backups."""

	def tearDown(self):
		frappe.db.rollback()

	def _sql_to_python(self, weekday: int) -> int:
		"""
		Convert weekday from sql standard to python.

		sql:    1-7 => sun-sat
		python: 0-6 => mon-sun
		"""
		return (weekday + 5) % 7

	def _is_weekly_backup_day(self, day: date) -> bool:
		return day.weekday() == self._sql_to_python(GFS.weekly_backup_day)

	def _is_monthly_backup_day(self, day: date) -> bool:
		return day.day == GFS.monthly_backup_day

	def _is_yearly_backup_day(self, day: date) -> bool:
		return day.timetuple().tm_yday == GFS.yearly_backup_day

	def test_only_daily_backups_longer_than_limit_deleted(self):
		"""Ensure only daily backups kept for longer than limit are deleted."""
		site = create_test_site("testsubdomain")
		oldest_allowed_daily = date.today() - timedelta(days=GFS.daily)
		older = oldest_allowed_daily - timedelta(days=1)
		newer = oldest_allowed_daily + timedelta(days=1)
		while (
			self._is_weekly_backup_day(older)
			or self._is_monthly_backup_day(older)
			or self._is_yearly_backup_day(older)
		):
			older -= timedelta(days=1)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_daily)
		older_backup = create_test_site_backup(site.name, older)
		newer_backup = create_test_site_backup(site.name, newer)

		gfs = GFS()
		gfs.expire_offsite_backups(site)

		limit_backup.reload()
		older_backup.reload()
		newer_backup.reload()

		self.assertEqual(limit_backup.files_availability, "Available")
		self.assertEqual(older_backup.files_availability, "Unavailable")
		self.assertEqual(newer_backup.files_availability, "Available")

	def _get_next_weekly_backup_day(self, day: date) -> date:
		backup_day = self._sql_to_python(GFS.weekly_backup_day)
		return day + timedelta(backup_day - day.weekday())

	def _get_previous_weekly_backup_day(self, day: date) -> date:
		backup_day = self._sql_to_python(GFS.weekly_backup_day)
		return day - timedelta(7 - (backup_day - day.weekday()))

	def test_only_weekly_backups_longer_than_limit_deleted(self):
		"""Ensure only weekly backups kept for longer than limit are deleted."""
		site = create_test_site("testsubdomain")
		weekly_backup_day = self._sql_to_python(GFS.weekly_backup_day)
		a_month_ago = date.today() - timedelta(weeks=4)
		oldest_allowed_weekly = (
			a_month_ago
			if a_month_ago.weekday() == weekly_backup_day
			else self._get_next_weekly_backup_day(a_month_ago)
		)
		older = self._get_previous_weekly_backup_day(oldest_allowed_weekly)
		while self._is_monthly_backup_day(older) or self._is_yearly_backup_day(older):
			older -= self._get_previous_weekly_backup_day(older)
		newer = self._get_next_weekly_backup_day(oldest_allowed_weekly)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_weekly)
		older_backup = create_test_site_backup(site.name, older)
		newer_backup = create_test_site_backup(site.name, newer)

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
		older = self._get_previous_monthly_backup_day(oldest_allowed_monthly)
		newer = self._get_next_monthly_backup_day(oldest_allowed_monthly)
		while self._is_yearly_backup_day(older):
			older -= self._get_previous_monthly_backup_day(older)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_monthly)
		older_backup = create_test_site_backup(site.name, older)
		newer_backup = create_test_site_backup(site.name, newer)

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
		older = self._get_previous_yearly_backup_day(
			oldest_allowed_yearly
		)
		newer = self._get_next_yearly_backup_day(
			oldest_allowed_yearly
		)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_yearly)
		older_backup = create_test_site_backup(site.name, older)
		newer_backup = create_test_site_backup(site.name, newer)

		gfs = GFS()
		gfs.expire_offsite_backups(site)

		limit_backup.reload()
		older_backup.reload()
		newer_backup.reload()

		self.assertEqual(limit_backup.files_availability, "Available")
		self.assertEqual(older_backup.files_availability, "Unavailable")
		self.assertEqual(newer_backup.files_availability, "Available")

	# @patch("press.press.cleanup.delete_remote_backup_objects")
	# def test_delete_remote_backup_objects_called(self, mock_del_remote_backup_objects):
	# 	"""Ensure delete_remote_backup_objects is called when backup is to be deleted."""
	# 	# XXX: might autocommit if you make too many docs
	# 	site = create_test_site("testsubdomain")
	# 	today = date.today()
	# 	oldest_daily = today - timedelta(GFS.daily)
	# 	create_test_site_backup(site.name, oldest_daily)
	# 	create_test_site_backup(site.name, oldest_daily - timedelta(1))
	# 	create_test_site_backup(site.name, oldest_daily + timedelta(1))
	# 	gfs = GFS()
	# 	gfs.cleanup()
	# 	mock_del_remote_backup_objects.assert_called_once()
	# 	print("*"*20)
	# 	print("*"*20)
	# 	print(mock_del_remote_backup_objects.call_args.args)
	# 	print("*"*20)
	# 	print("*"*20)
	# 	self.assertEqual(
	# 		len(mock_del_remote_backup_objects.call_args.args), 3 * 2
	# 	)

	# TODO test multiple sites
