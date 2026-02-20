# Copyright (c) 2020, Frappe and Contributors
# See license.txt
from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob, process_job_updates
from press.press.doctype.remote_file.test_remote_file import create_test_remote_file
from press.press.doctype.site.test_site import create_test_site
from press.press.doctype.site_activity.test_site_activity import create_test_site_activity

if TYPE_CHECKING:
	from datetime import datetime


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
def create_test_site_backup(
	site: str,
	creation: datetime | None = None,
	files_availability: str = "Available",
	offsite: bool = True,
	status: str = "Success",
):
	"""
	Create test site backup doc for required timestamp.

	Makes offsite backups by default along with remote files.
	"""
	creation = creation or frappe.utils.now_datetime()
	params_dict = {
		"doctype": "Site Backup",
		"status": status,
		"site": site,
		"files_availability": files_availability,
		"offsite": offsite,
		"with_files": offsite,
	}
	if offsite:
		params_dict["remote_public_file"] = create_test_remote_file(site, creation).name
		params_dict["remote_private_file"] = create_test_remote_file(site, creation).name
		params_dict["remote_database_file"] = create_test_remote_file(site, creation).name
	site_backup = frappe.get_doc(params_dict).insert(ignore_if_duplicate=True)

	site_backup.db_set("creation", creation)
	site_backup.reload()
	return site_backup


class TestSiteBackup(FrappeTestCase):
	def setUp(self):
		self.site = create_test_site(subdomain="breadshop")
		self.site_backup = create_test_site_backup(
			site=self.site.name,
			files_availability="Unavailable",
			offsite=False,
			status="Pending",
		)
		self.job = frappe.get_doc("Agent Job", self.site_backup.job)

	def tearDown(self):
		frappe.db.rollback()

	def test_backup_job_callback_with_only_database(self):
		self.job.db_set("status", "Success")
		self.job.db_set(
			"data",
			json.dumps(
				{
					"backups": {
						"database": {
							"file": "breadshop_database.sql.gz",
							"path": "/benches/breadshop_database.sql.gz",
							"size": 12345,
							"url": "https://breadshop.com/backups/breadshop-database.sql.gz",
						},
					},
					"offsite": {},
				}
			),
		)
		process_job_updates(self.job.name)
		self.site_backup.reload()
		self.assertEqual(self.site_backup.status, "Success")
		self.assertEqual(self.site_backup.database_file, "breadshop_database.sql.gz")
		self.assertEqual(self.site_backup.database_size, "12345")
		self.assertEqual(
			self.site_backup.database_url,
			"https://breadshop.com/backups/breadshop-database.sql.gz",
		)

	def test_backup_job_callback_with_config(self):
		self.job.db_set("status", "Success")
		self.job.db_set(
			"data",
			json.dumps(
				{
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
					},
					"offsite": {},
				}
			),
		)
		process_job_updates(self.job.name)
		self.site_backup.reload()
		self.assertEqual(self.site_backup.status, "Success")
		self.assertEqual(self.site_backup.database_file, "breadshop_database.sql.gz")
		self.assertEqual(self.site_backup.database_size, "12345")
		self.assertEqual(
			self.site_backup.database_url,
			"https://breadshop.com/backups/breadshop-database.sql.gz",
		)
		self.assertEqual(self.site_backup.config_file, "breadshop_config.json")
		self.assertEqual(self.site_backup.config_file_size, "12345")
		self.assertEqual(
			self.site_backup.config_file_url,
			"https://breadshop.com/backups/breadshop-config.json",
		)

	def test_backup_job_callback_with_files(self):
		self.job.db_set("status", "Success")
		self.job.db_set(
			"data",
			json.dumps(
				{
					"backups": {
						"database": {
							"file": "breadshop_database.sql.gz",
							"path": "/benches/breadshop_database.sql.gz",
							"size": 12345,
							"url": "https://breadshop.com/backups/breadshop-database.sql.gz",
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
					"offsite": {},
				}
			),
		)
		process_job_updates(self.job.name)
		self.site_backup.reload()
		self.assertEqual(self.site_backup.status, "Success")
		self.assertEqual(self.site_backup.database_file, "breadshop_database.sql.gz")
		self.assertEqual(self.site_backup.database_size, "12345")
		self.assertEqual(
			self.site_backup.database_url,
			"https://breadshop.com/backups/breadshop-database.sql.gz",
		)
		self.assertEqual(self.site_backup.public_file, "breadshop_public_files.tar")
		self.assertEqual(self.site_backup.public_size, "12345")
		self.assertEqual(
			self.site_backup.public_url,
			"https://breadshop.com/backups/breadshop-public-files.tar",
		)
		self.assertEqual(self.site_backup.private_file, "breadshop_private_files.tar")
		self.assertEqual(self.site_backup.private_size, "12345")
		self.assertEqual(
			self.site_backup.private_url,
			"https://breadshop.com/backups/breadshop-private-files.tar",
		)

	def test_backup_job_callback_with_offsite(self):
		self.job.db_set("status", "Success")
		self.job.db_set(
			"data",
			json.dumps(
				{
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
			),
		)

		process_job_updates(self.job.name)
		self.site_backup.reload()
		self.assertEqual(self.site_backup.status, "Success")
		self.assertTrue(self.site_backup.remote_database_file)
		self.assertTrue(self.site_backup.remote_public_file)
		self.assertTrue(self.site_backup.remote_private_file)
		self.assertTrue(self.site_backup.remote_config_file)

	def test_archiving_site_with_offsite_backup_creates_site_backup_record(self):
		"""
		When a site is archived after taking an offsite backup, test if a Site Backup record is created from the 'Archive Site' agent job's response.
		"""
		from press.press.doctype.site_backup.site_backup import (
			_create_site_backup_from_agent_job,
		)

		archive_job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"job_type": "Archive Site",
				"site": self.site.name,
				"server_type": "Server",
				"server": self.site.server,
				"request_method": "POST",
				"request_path": f"benches/{self.site.bench}/sites/{self.site.name}/archive",
				"request_data": "{}",
				"status": "Success",
				"data": json.dumps(
					{
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
								"size": 54321,
								"url": "https://breadshop.com/backups/breadshop-config.json",
							},
							"public": {
								"file": "breadshop_public_files.tar",
								"path": "/benches/breadshop_public_files.tar",
								"size": 99999,
								"url": "https://breadshop.com/backups/breadshop-public-files.tar",
							},
							"private": {
								"file": "breadshop_private_files.tar",
								"path": "/benches/breadshop_private_files.tar",
								"size": 88888,
								"url": "https://breadshop.com/backups/breadshop-private-files.tar",
							},
						},
						"offsite": {
							"breadshop_database.sql.gz": "s3://bucket/breadshop_database.sql.gz",
							"breadshop_config.json": "s3://bucket/breadshop_config.json",
							"breadshop_public_files.tar": "s3://bucket/breadshop_public_files.tar",
							"breadshop_private_files.tar": "s3://bucket/breadshop_private_files.tar",
						},
					}
				),
			}
		).insert()

		# Create the required backup steps with Success status
		frappe.get_doc(
			{
				"doctype": "Agent Job Step",
				"agent_job": archive_job.name,
				"step_name": "Backup Site",
				"status": "Success",
			}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Agent Job Step",
				"agent_job": archive_job.name,
				"step_name": "Upload Site Backup to S3",
				"status": "Success",
			}
		).insert()

		# Invoke the function to create Site Backup
		_create_site_backup_from_agent_job(archive_job)

		# verify Site Backup record creation
		site_backup = frappe.get_doc("Site Backup", {"job": archive_job.name})

		self.assertEqual(site_backup.status, "Success")
		self.assertEqual(site_backup.files_availability, "Available")
		self.assertEqual(site_backup.offsite, 1)
		self.assertEqual(site_backup.with_files, 1)
		self.assertEqual(site_backup.site, self.site.name)

		# Verify database, config and public and private file backup
		self.assertEqual(site_backup.database_file, "breadshop_database.sql.gz")
		self.assertEqual(site_backup.database_size, "12345")
		self.assertTrue(site_backup.remote_database_file)

		self.assertEqual(site_backup.config_file, "breadshop_config.json")
		self.assertEqual(site_backup.config_file_size, "54321")
		self.assertTrue(site_backup.remote_config_file)

		self.assertEqual(site_backup.public_file, "breadshop_public_files.tar")
		self.assertEqual(site_backup.public_size, "99999")
		self.assertTrue(site_backup.remote_public_file)

		self.assertEqual(site_backup.private_file, "breadshop_private_files.tar")
		self.assertEqual(site_backup.private_size, "88888")
		self.assertTrue(site_backup.remote_private_file)

		# Verify remote files were created
		remote_files = frappe.get_all("Remote File", {"site": self.site.name})
		self.assertEqual(len(remote_files), 4)

		for remote_file in remote_files:
			remote_file_doc = frappe.get_doc("Remote File", remote_file.name)
			self.assertEqual(remote_file_doc.site, self.site.name)
			self.assertIsNotNone(remote_file_doc.file_path)
			self.assertIsNotNone(remote_file_doc.file_name)

	def test_cleanup_archived_site_backups(self):
		"""Clear up backups if the site was archived before 6 months"""
		from press.press.doctype.site_backup.site_backup import cleanup_archived_site_backups

		site = create_test_site(subdomain="old-archive")
		site.db_set("status", "Archived")

		backup = create_test_site_backup(site=site.name, offsite=True, files_availability="Available")

		archive_job = frappe.get_doc(
			{
				"doctype": "Agent Job",
				"job_type": "Archive Site",
				"site": site.name,
				"server_type": "Server",
				"server": site.server,
				"request_method": "POST",
				"request_path": f"benches/{site.bench}/sites/{site.name}/archive",
				"request_data": "{}",
				"status": "Success",
			}
		).insert()

		activity = create_test_site_activity(site.name, "Archive")
		activity.db_set("job", archive_job.name)
		activity.db_set(
			"creation",
			frappe.utils.add_to_date(frappe.utils.now(), months=-7),
		)

		cleanup_archived_site_backups()

		backup.reload()
		self.assertEqual(backup.files_availability, "Unavailable")
