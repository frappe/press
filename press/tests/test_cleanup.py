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
