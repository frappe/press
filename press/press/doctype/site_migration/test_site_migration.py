# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import frappe
from unittest.mock import patch

from frappe.core.utils import find

from press.press.doctype.remote_file.remote_file import RemoteFile

from frappe.tests.utils import FrappeTestCase
from press.press.doctype.agent_job.agent_job import poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import fake_agent_job

from press.press.doctype.site.test_site import create_test_bench, create_test_site
from press.press.doctype.site_migration.site_migration import SiteMigration

BACKUP_JOB_RES = {
	"backups": {
		"database": {
			"file": "a.sql.gz",
			"path": "/home/frappe/a.sql.gz",
			"size": 1674818,
			"url": "https://a.com/a.sql.gz",
		},
		"public": {
			"file": "b.tar",
			"path": "/home/frappe/b.tar",
			"size": 1674818,
			"url": "https://a.com/b.tar",
		},
		"private": {
			"file": "a.tar",
			"path": "/home/frappe/a.tar",
			"size": 1674818,
			"url": "https://a.com/a.tar",
		},
		"site_config": {
			"file": "a.json",
			"path": "/home/frappe/a.json",
			"size": 595,
			"url": "https://a.com/json",
		},
	},
	"offsite": {
		"a.sql.gz": "bucket.frappe.cloud/2023-10-10/a.sql.gz",
		"a.tar": "bucket.frappe.cloud/2023-10-10/a.tar",
		"b.tar": "bucket.frappe.cloud/2023-10-10/b.tar",
		"a.json": "bucket.frappe.cloud/2023-10-10/a.json",
	},
}


@patch.object(RemoteFile, "download_link", new="http://test.com")
class TestSiteMigration(FrappeTestCase):
	def test_in_cluster_site_migration_goes_through_all_steps_and_updates_site(self):
		site = create_test_site()
		bench = create_test_bench()
		site_migration = frappe.get_doc(
			{
				"doctype": "Site Migration",
				"site": site.name,
				"destination_bench": bench.name,
			}
		).insert()

		with fake_agent_job("Update Site Configuration"), fake_agent_job(
			"Backup Site",
			data=BACKUP_JOB_RES,
		), fake_agent_job("New Site from Backup"), fake_agent_job(
			"Archive Site"
		), fake_agent_job(
			"Remove Site from Upstream"
		), fake_agent_job(
			"Add Site to Upstream"
		), fake_agent_job(
			"Update Site Configuration"
		):
			site_migration.start()
			poll_pending_jobs()
			poll_pending_jobs()
			poll_pending_jobs()
			poll_pending_jobs()
			poll_pending_jobs()
			poll_pending_jobs()
			poll_pending_jobs()
			site_migration.reload()
			self.assertEqual(site_migration.status, "Running")
			poll_pending_jobs()
		site_migration.reload()
		self.assertEqual(site_migration.status, "Success")
		site.reload()
		self.assertEqual(site.status, "Active")
		self.assertEqual(site.bench, bench.name)
		self.assertEqual(site.server, bench.server)

	def test_site_is_activated_on_failure_when_possible(self):
		site = create_test_site()
		bench = create_test_bench()
		site_migration = frappe.get_doc(
			{
				"doctype": "Site Migration",
				"site": site.name,
				"destination_bench": bench.name,
			}
		).insert()

		with fake_agent_job("Update Site Configuration"), fake_agent_job(
			"Backup Site",
			data=BACKUP_JOB_RES,
		), fake_agent_job("New Site from Backup"), fake_agent_job(
			"Archive Site", status="Failure"
		), fake_agent_job(
			"Update Site Configuration"
		):
			site_migration.start()
			poll_pending_jobs()
			poll_pending_jobs()
			poll_pending_jobs()
			site_migration.reload()
			self.assertEqual(site_migration.status, "Failure")
			site.reload()
			self.assertEqual(site.status, "Active")

	def test_site_archived_on_destinataion_on_failure(self):
		site = create_test_site()
		bench = create_test_bench()
		site_migration: SiteMigration = frappe.get_doc(
			{
				"doctype": "Site Migration",
				"site": site.name,
				"destination_bench": bench.name,
			}
		).insert()

		with fake_agent_job("Update Site Configuration"), fake_agent_job(
			"Backup Site",
			data=BACKUP_JOB_RES,
		), fake_agent_job("New Site from Backup", "Failure"), fake_agent_job(
			"Archive Site",  # archive site on destination (retry)
		), fake_agent_job(
			"Update Site Configuration"
		):
			site_migration.start()
			poll_pending_jobs()
			poll_pending_jobs()
			poll_pending_jobs()  # archive on destination
			poll_pending_jobs()  # restore on destination
			site_migration.reload()
			self.assertEqual(site_migration.status, "Failure")
			archive_job_count = frappe.db.count(
				"Agent Job", {"job_type": "Archive Site", "site": site.name, "server": bench.server}
			)
			self.assertEqual(archive_job_count, 2)

	def test_site_not_archived_on_destinataion_on_failure_if_site_archived_on_source(self):
		site = create_test_site()
		bench = create_test_bench()
		site_migration: SiteMigration = frappe.get_doc(
			{
				"doctype": "Site Migration",
				"site": site.name,
				"destination_bench": bench.name,
			}
		).insert()

		with fake_agent_job("Update Site Configuration"), fake_agent_job(
			"Backup Site",
			data=BACKUP_JOB_RES,
		), fake_agent_job("New Site from Backup"), fake_agent_job(
			"Archive Site",  # both archives
		), fake_agent_job(
			"Remove Site from Upstream"
		), fake_agent_job(
			"Add Site to Upstream", "Failure"
		):
			site_migration.start()
			poll_pending_jobs()
			poll_pending_jobs()
			poll_pending_jobs()  # archive on destination
			poll_pending_jobs()  # restore on destination
			poll_pending_jobs()  # archive on source
			poll_pending_jobs()  # remove from source proxy
			poll_pending_jobs()  # restore on dest proxy

		site_migration.reload()
		self.assertEqual(site_migration.status, "Failure")
		self.assertEqual(
			find(
				site_migration.steps,
				lambda x: x.method_name == SiteMigration.restore_site_on_destination_proxy.__name__,
			).status,
			"Failure",
		)  # step after archive site on source failed
		self.assertEqual(
			frappe.db.count(
				"Agent Job", {"job_type": "Archive Site", "site": site.name, "server": bench.server}
			),
			1,
		)  # only first archive on dest job ran
