# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def execute():
	"""Add a site field to existing Remote File documents to track Offsite Backups via dashboard"""
	offsite_backups = frappe.get_all(
		"Site Backup",
		fields=["site", "remote_database_file", "remote_public_file", "remote_private_file"],
		filters={"offsite": 1},
	)

	for backup in offsite_backups:
		remote_database_file, remote_public_file, remote_private_file = (
			backup.get("remote_database_file"),
			backup.get("remote_public_file"),
			backup.get("remote_private_file"),
		)
		site = backup.get("site")

		for name in [remote_database_file, remote_public_file, remote_private_file]:
			frappe.db.set_value("Remote File", name, "site", site)
