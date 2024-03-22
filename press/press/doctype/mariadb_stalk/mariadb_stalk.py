# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import gzip

import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now

from press.utils import log_error
from datetime import datetime
from frappe.utils import convert_utc_to_system_timezone, add_to_date, now_datetime


class MariaDBStalk(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.mariadb_stalk_diagnostic.mariadb_stalk_diagnostic import (
			MariaDBStalkDiagnostic,
		)

		diagnostics: DF.Table[MariaDBStalkDiagnostic]
		server: DF.Link | None
		timestamp: DF.Datetime | None
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=30):
		table = frappe.qb.DocType("MariaDB Stalk")
		stalks = frappe.db.get_values(
			table, filters=table.creation < (Now() - Interval(days=days))
		)
		for stalk in stalks:
			try:
				stalk = frappe.get_doc("MariaDB Stalk", stalk)
				stalk.create_json_gz_file()
				stalk.delete(delete_permanently=True)
				frappe.db.commit()
			except Exception:
				log_error("MariaDB Stalk Delete Error")
				frappe.db.rollback()

	def create_json_gz_file(self):
		filename = f"mariadb-stalk-{self.server}-{self.timestamp}.json.gz"
		encoded = frappe.safe_encode(self.as_json())
		compressed = gzip.compress(encoded)
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": filename,
				"content": compressed,
				"is_private": True,
			}
		)
		file.insert()


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
	for stalk in server.get_stalks():
		timestamp = convert_utc_to_system_timezone(
			datetime.fromisoformat(stalk["timestamp"])
		).replace(tzinfo=None)
		# To avoid fetching incomplete stalks, wait for 5 minutes
		if not now_datetime() > add_to_date(timestamp, minutes=5):
			continue
		# Don't fetch old stalks
		if now_datetime() > add_to_date(timestamp, days=15):
			continue
		if frappe.db.exists("MariaDB Stalk", {"server": server.name, "timestamp": timestamp}):
			continue
		try:
			doc = frappe.new_doc("MariaDB Stalk")
			doc.server = server.name
			doc.timestamp = timestamp
			for diagnostic in server.get_stalk(stalk["name"]):
				doc.append("diagnostics", diagnostic)
			doc.insert()
			frappe.db.commit()
		except Exception:
			log_error("MariaDB Stalk Error", server=server, stalk=stalk)
			frappe.db.rollback()
