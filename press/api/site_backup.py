from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
	from press.press.doctype.site_backup.site_backup import SiteBackup


@frappe.whitelist(allow_guest=True, methods="POST")
def create_snapshot(name: str, key: str):
	"""
	This API will be called by agent during physical backup of database server.
	Once, agent prepare the specific database for backup, it will call this API to create a snapshot of the database.
	Because we need to hold the lock on the database for the duration of the backup.
	Only after the snapshot is created, the agent will release the lock on the database.
	"""
	current_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		site_backup: SiteBackup = frappe.get_doc("Site Backup", name)
		if not (key and site_backup.snapshot_request_key == key):
			frappe.throw("Invalid key for snapshot creation")
		site_backup.create_database_snapshot()
		site_backup.reload()
		# Re-verify if the snapshot was created and linked to the site backup
		if not site_backup.database_snapshot:
			frappe.throw("Failed to create a snapshot for the database server")
	except Exception as e:
		raise e
	finally:
		frappe.set_user(current_user)
