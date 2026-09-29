# Copyright (c) 2020, Frappe and Contributors
# See license.txt

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import boto3
import frappe
from frappe.tests.utils import FrappeTestCase
from moto import mock_aws

from press.press.doctype.remote_file.remote_file import (
	RemoteFile,
	get_remote_key,
	get_team_prefix,
	get_untracked_files_to_delete,
	poll_file_statuses_from_bucket,
)
from press.tests.before_test import freeze_time

UPLOADS_BUCKET = "test-remote-uploads"
SWEEP_BUCKET = "test-sweep-backups"


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

	@patch.object(RemoteFile, "ensure_team_set", new=Mock())
	def test_uploaded_file_without_team_is_rejected(self):
		"""ensure_team_set leaves the team empty when the site has none."""
		frappe.db.set_single_value("Press Settings", "remote_uploads_bucket", UPLOADS_BUCKET)

		with self.assertRaises(frappe.PermissionError) as context:
			frappe.get_doc(
				{
					"doctype": "Remote File",
					"bucket": UPLOADS_BUCKET,
					"file_path": "anything/database.sql.gz",
				}
			).insert()

		self.assertIn("must belong to a team", str(context.exception))

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

	@patch.object(frappe.db, "commit", new=Mock())
	def test_backfill_patch_sets_team_from_the_files_own_site(self):
		from press.patches.v0_8_0.set_team_on_remote_file import execute
		from press.press.doctype.site.test_site import create_test_site
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		site = create_test_site(subdomain="breadshop", team=team.name)
		remote_file = create_test_remote_file(site=site.name, file_path="benches/db.sql.gz")
		frappe.db.set_value("Remote File", remote_file.name, "team", None)

		execute()

		self.assertEqual(frappe.db.get_value("Remote File", remote_file.name, "team"), team.name)

	@patch.object(frappe.db, "commit", new=Mock())
	def test_backfill_patch_sets_team_from_the_site_that_uses_the_file(self):
		"""Uploaded files carry no site of their own."""
		from press.patches.v0_8_0.set_team_on_remote_file import execute
		from press.press.doctype.site.test_site import create_test_site
		from press.press.doctype.team.test_team import create_test_team

		team = create_test_team()
		site = create_test_site(subdomain="breadshop", team=team.name)
		remote_file = create_test_remote_file(file_path="uploads/db.sql.gz")
		frappe.db.set_value("Remote File", remote_file.name, "team", None)
		frappe.db.set_value("Site", site.name, "remote_database_file", remote_file.name)

		execute()

		self.assertEqual(frappe.db.get_value("Remote File", remote_file.name, "team"), team.name)

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

	def test_untracked_files_are_deleted_only_once_older_than_any_running_backup_job(self):
		now = datetime.now(timezone.utc)
		available_files = {
			"old-untracked.sql.gz": now - timedelta(days=3),
			"fresh-untracked.sql.gz": now - timedelta(hours=1),
			"old-tracked.sql.gz": now - timedelta(days=3),
		}

		to_delete = get_untracked_files_to_delete(available_files, {"old-tracked.sql.gz"})

		self.assertEqual(to_delete, ["old-untracked.sql.gz"])

	@mock_aws
	def test_bucket_poll_deletes_only_old_untracked_files_and_keeps_in_flight_backups(self):
		s3 = boto3.client("s3", region_name="us-east-1")
		s3.create_bucket(Bucket=SWEEP_BUCKET)
		with freeze_time(datetime.now(timezone.utc) - timedelta(days=9), is_utc=True):
			s3.put_object(Bucket=SWEEP_BUCKET, Key="site/old/orphan-database.sql.gz", Body=b"backup")
			s3.put_object(Bucket=SWEEP_BUCKET, Key="site/old/tracked-database.sql.gz", Body=b"backup")
		# Uploaded by a backup job that hasn't finished, so it has no Remote File yet
		s3.put_object(Bucket=SWEEP_BUCKET, Key="site/today/in-flight-database.sql.gz", Body=b"backup")
		create_test_remote_file(bucket=SWEEP_BUCKET, file_path="site/old/tracked-database.sql.gz")
		bucket = {
			"name": SWEEP_BUCKET,
			"region": "us-east-1",
			"access_key_id": "test",
			"secret_access_key": "test",  # pragma: allowlist secret
		}

		with patch.object(frappe.db, "commit", new=Mock()):
			poll_file_statuses_from_bucket(bucket)

		remaining = {obj["Key"] for obj in s3.list_objects_v2(Bucket=SWEEP_BUCKET)["Contents"]}
		self.assertEqual(
			remaining, {"site/old/tracked-database.sql.gz", "site/today/in-flight-database.sql.gz"}
		)
