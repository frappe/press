# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SSHSessionLog(Document):
	@staticmethod
	def create_ssh_session_log(log: dict, server: str, server_type: str):
		try:
			ssh_session_log = frappe.get_doc(
				{
					"doctype": "SSH Session Log",
					"server_type": server_type,
					"server": server,
					"created_at": log["created_at"],
					"ssh_user": log["user"],
					"filename": log["name"],
					"session_id": log["session_id"],
				}
			)

			ssh_session_log.insert(ignore_permissions=True, ignore_mandatory=True)
		except frappe.DuplicateEntryError:
			pass

	@staticmethod
	def update_ssh_session_log(log: str, content: str):
		ssh_session_log = frappe.get_doc("SSH Session Log", log)
		ssh_session_log.ssh_activity_log = content
		ssh_session_log.save(ignore_permissions=True)


def get_activity_log_from_db(filename):
	try:
		log = frappe.get_doc("SSH Session Log", filename)

		if not log.ssh_activity_log:
			return None

		return {
			"session_user": log.ssh_user,
			"session_id": log.session_id,
			"content": log.ssh_activity_log,
		}
	except frappe.DoesNotExistError:
		pass
