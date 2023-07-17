# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and Contributors
# See license.txt


import json
from datetime import datetime
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.agent_job.agent_job import AgentJob, process_job_updates
from press.press.doctype.remote_file.test_remote_file import create_test_remote_file
from press.press.doctype.site.test_site import create_test_site


@patch.object(AgentJob, "enqueue_http_request", new=Mock())
def create_test_site_backup(
	site: str,
	creation: datetime = None,
	files_availability: str = "Available",
	offsite: bool = True,
	status: str = "Success",
):
	"""
	Create test site backup doc for required timestamp.

	Makes offsite backups by default along with remote files.
	"""
	if not creation:
		creation = datetime.now()
	params_dict = {
		"doctype": "Site Backup",
		"status": status,
		"site": site,
		"files_availability": files_availability,
		"offsite": offsite,
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
