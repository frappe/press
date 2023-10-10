# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from press.press.doctype.agent_job.agent_job import poll_pending_jobs
from press.press.doctype.agent_job.test_agent_job import fake_agent_job

from press.press.doctype.site.test_site import create_test_bench, create_test_site


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
			data={
				"backups": {
					"database": {
						"file": "a.sql.gz",
						"path": "/home/frappe/a.sql.gz",
						"size": 1674818,
						"url": "https://a.com/a.sql.gz",
					},
					"site_config": {
						"file": "a.json",
						"path": "/home/frappe/a.json",
						"size": 595,
						"url": "https://a.com/json",
					},
				},
				"offsite": {},
			},
		), fake_agent_job("New Site From Backup"), fake_agent_job(
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
		self.assertEqual(site_migration.status, "Success")
