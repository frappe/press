# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.utils import log_error
from datetime import datetime
from frappe.utils import convert_utc_to_system_timezone


class MariaDBStalk(Document):
	pass


def fetch_stalks():
	for server in frappe.get_all(
		"Database Server", {"status": "Active", "is_stalk_setup": True}, pluck="name"
	):
		frappe.enqueue(
			"press.press.doctype.mariadb_stalk.mariadb_stalk.fetch_server_stalks",
			server=server,
			job_id=f"fetch_mariadb_stalk:{server}",
		)


def fetch_server_stalks(server):
	server = frappe.get_cached_doc("Database Server", server)
	for stalk in server.fetch_stalks():
		timestamp = convert_utc_to_system_timezone(
			datetime.fromisoformat(stalk["timestamp"])
		).replace(tzinfo=None)
		if frappe.db.exists("MariaDB Stalk", {"server": server.name, "timestamp": timestamp}):
			continue
		try:
			doc = frappe.new_doc("MariaDB Stalk")
			doc.server = server.name
			doc.timestamp = timestamp
			for diagnostic in server.fetch_stalk(stalk["name"]):
				doc.append("diagnostics", diagnostic)
			doc.insert()
			frappe.db.commit()
		except Exception:
			log_error("MariaDB Stalk Error", server=server, stalk=stalk)
			frappe.db.rollback()
