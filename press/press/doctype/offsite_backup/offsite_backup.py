# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
from press.agent import Agent


def take_offsite_backups():
	benches = [x.name for x in frappe.get_all(
		"Bench",
		fields=["name"],
		filters={"status": "Active"}
	)]
	for bench in benches:
		doc = frappe.new_doc("Offsite Backup")
		doc.bench = bench
		doc.insert()


def process_offsite_backup_job_update(job):
	offsite_backup = frappe.get_all(
		"Offsite Backup", fields=["name", "status"], filters={"job": job.name}
	)[0]

	if job.status != offsite_backup.status:
		frappe.db.set_value("Offsite Backup", offsite_backup.name, "status", job.status)


class OffsiteBackup(Document):
	def after_insert(self):
		bench = frappe.get_doc("Bench", self.bench)
		settings = frappe.get_single("Press Settings")
		auth = {
			"ACCESS_KEY": settings.offsite_backups_access_key_id,
			"SECRET_KEY": get_decrypted_password(settings.offsite_backups_secret_access_key)
		}
		agent = Agent(bench.server)

		if not settings.aws_s3_bucket:
			frappe.throw("Offsite Backups aren't set yet")

		job = agent.offsite_backup(bench.name, settings.aws_s3_bucket, auth)
		frappe.db.set_value(self.doctype, self.name, "job", job.name)
