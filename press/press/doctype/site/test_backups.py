from press.press.doctype.site_backup.test_site_backup import create_test_site_backup
from press.press.doctype.site.test_site import create_test_site
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, Mock, patch

import frappe

from press.press.doctype.agent_job.agent_job import AgentJob
from press.press.doctype.site.backups import ScheduledBackupJob, start


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

	@patch.object(
		ScheduledBackupJob, "is_backup_hour", new=lambda self, x: True,  # always backup hour
	)
	@patch.object(
		ScheduledBackupJob,
		"take_offsite",
		new=lambda self, x, y: True,  # take offsite anyway
	)
	def test_offsite_taken_once_per_day(self):
		site = create_test_site()
		offsite_count_before = self._offsite_count(site.name)
		start()
		offsite_count_after = self._offsite_count(site.name)
		self.assertGreater(offsite_count_after, offsite_count_before)
		offsite_count_before = self._offsite_count(site.name)
		start()
		offsite_count_after = self._offsite_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	@patch.object(
		ScheduledBackupJob, "is_backup_hour", new=lambda self, x: True,  # always backup hour
	)
	def test_with_files_taken_once_per_day(self):
		site = create_test_site()
		offsite_count_before = self._with_files_count(site.name)
		start()
		offsite_count_after = self._with_files_count(site.name)
		self.assertGreater(offsite_count_after, offsite_count_before)
		offsite_count_before = self._with_files_count(site.name)
		start()
		offsite_count_after = self._with_files_count(site.name)
		self.assertEqual(offsite_count_after, offsite_count_before)

	def test_only_get_sites_without_backups_in_interval_hour(self):
		pass
