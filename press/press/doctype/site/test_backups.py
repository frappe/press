import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.backups import ScheduledBackupJob
from press.press.doctype.site.test_site import create_test_site


@patch("press.press.doctype.site.backups.frappe.db.commit", new=MagicMock)
@patch("press.press.doctype.site.backups.frappe.db.rollback", new=MagicMock)
@patch.object(AgentJob, "after_insert", new=Mock())
class TestScheduledBackupJob(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _offsite_count(self, site: str):
		return frappe.db.count("Site Backup", {"site": site, "offsite": True},)

	def _with_files_count(self, site: str):
		return frappe.db.count("Site Backup", {"site": site, "with_files": True},)

	def setUp(self):
		self.interval = 6
		frappe.db.set_value("Press Settings", "Press Settings", "backup_interval", 6)

	def _interval_hours_ago(self):
		return datetime.now() - timedelta(hours=self.interval + 1)

	@patch.object(
		ScheduledBackupJob, "is_backup_hour", new=lambda self, x: True,  # always backup hour
	)
	@patch.object(
		ScheduledBackupJob,
		"take_offsite",
		new=lambda self, x, y: True,  # take offsite anyway
	)
	def test_offsite_taken_once_per_day(self):
		site = create_test_site(creation=self._interval_hours_ago())
		job = ScheduledBackupJob()
		offsite_count_before = self._offsite_count(site.name)
		job.start()
		offsite_count_after = self._offsite_count(site.name)
		self.assertGreater(offsite_count_after, offsite_count_before)
		offsite_count_before = self._offsite_count(site.name)
		job.start()
		offsite_count_after = self._offsite_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	@patch.object(
		ScheduledBackupJob, "is_backup_hour", new=lambda self, x: True,  # always backup hour
	)
	def test_with_files_taken_once_per_day(self):
		site = create_test_site(creation=self._interval_hours_ago())
		job = ScheduledBackupJob()
		offsite_count_before = self._with_files_count(site.name)
		job.start()
		offsite_count_after = self._with_files_count(site.name)
		self.assertGreater(offsite_count_after, offsite_count_before)
		offsite_count_before = self._with_files_count(site.name)
		job.start()
		offsite_count_after = self._with_files_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)
