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
		job = agent.backup_site(site)
		frappe.db.set_value("Site Backup", self.name, "job", job.name)


def process_backup_site_job_update(job):
	backup = frappe.get_all(
		"Site Backup", fields=["name", "status"], filters={"job": job.name}
	)[0]
	if job.status != backup.status:
		frappe.db.set_value("Site Backup", backup.name, "status", job.status)
		if job.status == "Success":
			data = json.loads(job.data)
			frappe.db.set_value("Site Backup", backup.name, "size", data["size"])
			frappe.db.set_value("Site Backup", backup.name, "url", data["url"])
			frappe.db.set_value("Site Backup", backup.name, "database", data["database"])
