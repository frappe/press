# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

if TYPE_CHECKING:
	from datetime import datetime


def create_test_remote_file(
	site: str | None = None,
	creation: datetime | None = None,
	file_path: str | None = None,
	file_size: int = 1024,
	bucket: str | None = None,
):
	"""Create test remote file doc for required timestamp."""
	creation = creation or frappe.utils.now_datetime()
	remote_file = frappe.get_doc(
		{
			"doctype": "Remote File",
			"status": "Available",
			"site": site,
			"file_path": file_path,
			"file_size": file_size,
			"bucket": bucket,
		}
	).insert(ignore_if_duplicate=True)
	remote_file.db_set("creation", creation)
	remote_file.reload()
	return remote_file


OFFSITE_BACKUP_JOB_DATA = {
	"backups": {
		"database": {
			"file": "breadshop_database.sql.gz",
			"path": "/benches/breadshop_database.sql.gz",
			"size": 12345,
			"url": "https://breadshop.com/backups/breadshop-database.sql.gz",
		},
		"site_config": {
			"file": "breadshop_config.json",
			"path": "/benches/breadshop_config.json",
			"size": 12345,
			"url": "https://breadshop.com/backups/breadshop-config.json",
		},
		"public": {
			"file": "breadshop_public_files.tar",
			"path": "/benches/breadshop_public_files.tar",
			"size": 12345,
			"url": "https://breadshop.com/backups/breadshop-public-files.tar",
		},
		"private": {
			"file": "breadshop_private_files.tar",
			"path": "/benches/breadshop_private_files.tar",
			"size": 12345,
			"url": "https://breadshop.com/backups/breadshop-private-files.tar",
		},
	},
	"offsite": {
		"breadshop_database.sql.gz": "offsite.dev/breadshop_database.sql.gz",
		"breadshop_config.json": "offsite.dev/breadshop_config.json",
		"breadshop_public_files.tar": "offsite.dev/breadshop_public_files.tar",
		"breadshop_private_files.tar": "offsite.dev/breadshop_private_files.tar",
	},
}


class TestRemoteFile(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_offsite_backup_remote_files_belong_to_sites_team(self):
		"""Backup remote files are created in the agent job's callback, as Administrator."""
		from press.press.doctype.agent_job.agent_job import poll_pending_jobs
		from press.press.doctype.agent_job.test_agent_job import fake_agent_job
		from press.press.doctype.site.test_site import create_test_site
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		site = create_test_site(subdomain="breadshop", team=team.name)

		with fake_agent_job("Backup Site", data=OFFSITE_BACKUP_JOB_DATA):
			site.backup(with_files=True, offsite=True)
			poll_pending_jobs()

		backup = frappe.get_last_doc("Site Backup", {"site": site.name})
		self.assertEqual(backup.status, "Success")
		for remote_file in (
			backup.remote_database_file,
			backup.remote_public_file,
			backup.remote_private_file,
			backup.remote_config_file,
		):
			self.assertEqual(frappe.db.get_value("Remote File", remote_file, "team"), team.name)
