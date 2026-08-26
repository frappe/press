# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.remote_file.remote_file import get_remote_key, get_team_prefix

if TYPE_CHECKING:
	from datetime import datetime

UPLOADS_BUCKET = "test-remote-uploads"


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
		frappe.set_user("Administrator")

	def test_uploaded_file_path_outside_team_prefix_is_rejected(self):
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		frappe.db.set_single_value("Press Settings", "remote_uploads_bucket", UPLOADS_BUCKET)

		with self.assertRaises(frappe.PermissionError) as context:
			frappe.get_doc(
				{
					"doctype": "Remote File",
					"team": team.name,
					"bucket": UPLOADS_BUCKET,
					"file_path": f"{get_team_prefix('victim@example.com')}/1_2/database.sql.gz",
				}
			).insert()

		self.assertIn("is not under this team's upload prefix", str(context.exception))

	def test_uploaded_file_path_under_team_prefix_is_accepted(self):
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		frappe.db.set_single_value("Press Settings", "remote_uploads_bucket", UPLOADS_BUCKET)

		file_path = f"{get_team_prefix(team.name)}/1_2/database.sql.gz"
		remote_file = frappe.get_doc(
			{
				"doctype": "Remote File",
				"team": team.name,
				"bucket": UPLOADS_BUCKET,
				"file_path": file_path,
			}
		).insert()

		self.assertEqual(remote_file.file_path, file_path)

	def test_backup_file_in_another_bucket_is_not_checked_against_prefix(self):
		"""Backups are keyed by the agent and never carry a team prefix."""
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		frappe.db.set_single_value("Press Settings", "remote_uploads_bucket", UPLOADS_BUCKET)

		remote_file = frappe.get_doc(
			{
				"doctype": "Remote File",
				"team": team.name,
				"bucket": "offsite-backups",
				"file_path": "/benches/breadshop_database.sql.gz",
			}
		).insert()

		self.assertEqual(remote_file.file_path, "/benches/breadshop_database.sql.gz")

	def test_existing_uploaded_file_can_still_be_saved(self):
		"""The prefix rule applies on insert only, so old rows stay editable."""
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		remote_file = frappe.get_doc(
			{
				"doctype": "Remote File",
				"team": team.name,
				"file_path": "some/legacy/path.sql.gz",
			}
		).insert()

		frappe.db.set_single_value("Press Settings", "remote_uploads_bucket", UPLOADS_BUCKET)
		remote_file.bucket = UPLOADS_BUCKET
		remote_file.save()

		self.assertEqual(remote_file.file_path, "some/legacy/path.sql.gz")

	def test_absolute_upload_filename_stays_under_team_prefix(self):
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		frappe.set_user(team.user)

		key = get_remote_key("/etc/passwd")

		self.assertTrue(key.startswith(f"{get_team_prefix(team.name)}/"))
		self.assertTrue(key.endswith("/passwd"))

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
