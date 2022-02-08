import json
import unittest
from datetime import date, timedelta
from unittest.mock import Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.press_settings.test_press_settings import (
	create_test_press_settings,
)
from press.press.doctype.site.backups import FIFO, GFS
from press.press.doctype.site.backups import cleanup_offsite
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
		gfs.expire_offsite_backups()

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
			older = self._get_previous_weekly_backup_day(older)
		newer = self._get_next_weekly_backup_day(oldest_allowed_weekly)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_weekly)
		older_backup = create_test_site_backup(site.name, older)
		newer_backup = create_test_site_backup(site.name, newer)

		gfs = GFS()
		gfs.expire_offsite_backups()

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
			older = self._get_previous_monthly_backup_day(older)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_monthly)
		older_backup = create_test_site_backup(site.name, older)
		newer_backup = create_test_site_backup(site.name, newer)

		gfs = GFS()
		gfs.expire_offsite_backups()

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
		older = self._get_previous_yearly_backup_day(oldest_allowed_yearly)
		newer = self._get_next_yearly_backup_day(oldest_allowed_yearly)

		limit_backup = create_test_site_backup(site.name, oldest_allowed_yearly)
		older_backup = create_test_site_backup(site.name, older)
		newer_backup = create_test_site_backup(site.name, newer)

		gfs = GFS()
		gfs.expire_offsite_backups()

		limit_backup.reload()
		older_backup.reload()
		newer_backup.reload()

		self.assertEqual(limit_backup.files_availability, "Available")
		self.assertEqual(older_backup.files_availability, "Unavailable")
		self.assertEqual(newer_backup.files_availability, "Available")

	@patch("press.press.doctype.site.backups.delete_remote_backup_objects")
	@patch("press.press.doctype.site.backups.frappe.db.commit")
	def test_delete_remote_backup_objects_called(
		self, mock_frappe_commit, mock_del_remote_backup_objects
	):
		"""
		Ensure delete_remote_backup_objects is called when backup is to be deleted.

		(db commit call inside GFS.cleanup_offsite is mocked so tests don't break)
		"""
		site = create_test_site("testsubdomain")
		site2 = create_test_site("testsubdomain2")
		today = date.today()
		oldest_allowed_daily = today - timedelta(GFS.daily)
		older = oldest_allowed_daily - timedelta(days=1)
		newer = oldest_allowed_daily + timedelta(days=1)
		while (
			self._is_weekly_backup_day(older)
			or self._is_monthly_backup_day(older)
			or self._is_yearly_backup_day(older)
		):
			older -= timedelta(days=1)
		create_test_site_backup(site.name, older)
		create_test_site_backup(site2.name, older)
		create_test_site_backup(site.name, newer)
		create_test_site_backup(site2.name, newer)
		gfs = GFS()
		gfs.cleanup_offsite()
		mock_del_remote_backup_objects.assert_called_once()
		args, kwargs = mock_del_remote_backup_objects.call_args
		self.assertEqual(len(args[0]), 3 * 2, msg=mock_del_remote_backup_objects.call_args)


class TestFIFO(unittest.TestCase):
	"""Test FIFO backup rotation scheme."""

	def tearDown(self):
		frappe.db.rollback()

	def test_backups_older_than_number_specified_deleted(self):
		"""Ensure older backups in queue are deleted."""
		fifo = FIFO()
		fifo.offsite_backups_count = 2
		site = create_test_site("testsubdomain")
		older = create_test_site_backup(site.name, date.today() - timedelta(2))
		old = create_test_site_backup(site.name, date.today() - timedelta(1))
		new = create_test_site_backup(site.name)

		fifo.expire_offsite_backups()

		older.reload()
		old.reload()
		new.reload()

		self.assertEqual(older.files_availability, "Unavailable")
		self.assertEqual(old.files_availability, "Available")
		self.assertEqual(new.files_availability, "Available")

	@patch("press.press.doctype.site.backups.delete_remote_backup_objects")
	@patch("press.press.doctype.site.backups.frappe.db.commit")
	def test_delete_remote_backup_objects_called(
		self, mock_frappe_commit, mock_del_remote_backup_objects
	):
		"""
		Ensure delete_remote_backup_objects is called when backup is to be deleted.

		(db commit call inside GFS.cleanup_offsite is mocked so tests don't break)
		"""
		site = create_test_site("testsubdomain")
		site2 = create_test_site("testsubdomain2")

		fifo = FIFO()
		fifo.offsite_backups_count = 1

		create_test_site_backup(site.name, date.today() - timedelta(1))
		create_test_site_backup(site.name)
		create_test_site_backup(site2.name, date.today() - timedelta(1))
		create_test_site_backup(site2.name)

		fifo.cleanup_offsite()
		mock_del_remote_backup_objects.assert_called_once()
		args = mock_del_remote_backup_objects.call_args[0]
		self.assertEqual(len(args[0]), 3 * 2, msg=mock_del_remote_backup_objects.call_args)

	def test_press_setting_updates_new_object(self):
		"""Ensure updating press settings updates new FIFO objects."""
		press_settings = create_test_press_settings()
		press_settings.offsite_backups_count = 2
		press_settings.save()
		fifo = FIFO()
		self.assertEqual(fifo.offsite_backups_count, 2)


class TestBackupRotationScheme(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	@patch("press.press.doctype.site.backups.GFS")
	@patch("press.press.doctype.site.backups.FIFO")
	def test_press_setting_of_rotation_scheme_works(self, mock_FIFO, mock_GFS):
		"""Ensure setting rotation scheme in press settings affect rotation scheme used."""
		press_settings = create_test_press_settings()
		press_settings.backup_rotation_scheme = "FIFO"
		press_settings.save()
		cleanup_offsite()
		mock_FIFO.assert_called_once()
		mock_GFS.assert_not_called()

		mock_FIFO.reset_mock()
		mock_GFS.reset_mock()

		press_settings.backup_rotation_scheme = "Grandfather-father-son"
		press_settings.save()
		cleanup_offsite()
		mock_GFS.assert_called_once()
		mock_FIFO.assert_not_called()

	@patch("press.press.doctype.site.backups.delete_remote_backup_objects")
	@patch("press.press.doctype.site.backups.frappe.db.commit")
	def test_local_backups_are_expired(
		self, mock_frappe_commit, mock_del_remote_backup_objects
	):
		"""
		Ensure onsite backups are marked unavailable.

		Check backups older than 24hrs marked unavailable
		"""
		site = create_test_site("testsubdomain")
		site2 = create_test_site("testsubdomain2")

		backup_1_1 = create_test_site_backup(
			site.name, date.today() - timedelta(1), offsite=False
		)
		backup_1_2 = create_test_site_backup(site.name)
		backup_2_1 = create_test_site_backup(
			site2.name, date.today() - timedelta(2), offsite=False
		)
		backup_2_2 = create_test_site_backup(site2.name)

		GFS().expire_local_backups()

		backup_1_1.reload()
		backup_1_2.reload()
		backup_2_1.reload()
		backup_2_2.reload()

		self.assertEqual(backup_1_1.files_availability, "Unavailable")
		self.assertEqual(backup_1_2.files_availability, "Available")
		self.assertEqual(backup_2_1.files_availability, "Unavailable")
		self.assertEqual(backup_2_2.files_availability, "Available")

	@patch("press.press.doctype.site.backups.delete_remote_backup_objects")
	@patch("press.press.doctype.site.backups.frappe.db.commit")
	def test_local_backups_with_different_bench_configs_expire_sites(
		self, mock_frappe_commit, mock_del_remote_backup_objects
	):
		"""Ensure onsite backups are cleaned up respecting bench config."""
		site = create_test_site("testsubdomain")
		site2 = create_test_site("testsubdomain2")

		config = json.dumps({"keep_backups_for_hours": 50})
		frappe.db.set_value("Bench", site.bench, "config", config)

		backup_1_1 = create_test_site_backup(
			site.name, date.today() - timedelta(1), offsite=False
		)
		backup_1_2 = create_test_site_backup(site.name)
		backup_2_1 = create_test_site_backup(
			site2.name, date.today() - timedelta(2), offsite=False
		)
		backup_2_2 = create_test_site_backup(site2.name)

		GFS().expire_local_backups()

		backup_1_1.reload()
		backup_1_2.reload()
		backup_2_1.reload()
		backup_2_2.reload()

		self.assertEqual(backup_1_1.files_availability, "Available")
		self.assertEqual(backup_1_2.files_availability, "Available")
		self.assertEqual(backup_2_1.files_availability, "Unavailable")
		self.assertEqual(backup_2_2.files_availability, "Available")
