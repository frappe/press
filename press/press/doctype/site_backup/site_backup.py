# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from press.agent import Agent


class SiteBackup(Document):
	def after_insert(self):
		site = frappe.get_doc("Site", self.site)
		agent = Agent(site.server)
		job = agent.backup_site(site, self.with_files, self.offsite)
		frappe.db.set_value("Site Backup", self.name, "job", job.name)


def process_backup_site_job_update(job):
	backup = frappe.get_all(
		"Site Backup", fields=["name", "status"], filters={"job": job.name}
	)[0]
	if job.status != backup.status:
		frappe.db.set_value("Site Backup", backup.name, "status", job.status)
		if job.status == "Success":
			backup_data, offsite_backup_data = json.loads(job.data)
			frappe.db.set_value(
				"Site Backup",
				backup.name,
				{
					"database_size": backup_data["database"]["size"],
					"database_url": backup_data["database"]["url"],
					"database_file": backup_data["database"]["file"],
					"offsite_backup": json.dumps(offsite_backup_data, indent=4)
				},
			)
			if "private" in backup_data and "public" in backup_data:
				frappe.db.set_value(
					"Site Backup",
					backup.name,
					{
						"private_size": backup_data["private"]["size"],
						"private_url": backup_data["private"]["url"],
						"private_file": backup_data["private"]["file"],
						"public_size": backup_data["public"]["size"],
						"public_url": backup_data["public"]["url"],
						"public_file": backup_data["public"]["file"],
					},
				)
