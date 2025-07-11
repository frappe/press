# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.server.server import Server


class AddOnStorageLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		current_disk_usage: DF.Float
		database_server: DF.Link | None
		increased_from: DF.Float
		increased_to: DF.Float
		mountpoint: DF.Data | None
		reason: DF.SmallText | None
		server: DF.Link | None
	# end: auto-generated types

	def after_insert(self):
		"""Send add on storage notification"""
		server: Server | DatabaseServer = frappe.get_cached_doc(
			self.server if self.server else self.database_server, self.name
		)
		notify_email = frappe.get_value("Team", server.team, "notify_email")

		frappe.sendmail(
			recipients=notify_email,
			subject=f"Important: Server {server.name} storage space at 90%",
			template="disabled_auto_disk_expansion",
			args={
				"sever": server.name,
				"current_disk_usage": f"{self.current_disk_usage} GiB",
				"available_disk_space": f"{self.increased_from} GiB",
				"increase_by": f"{self.increased_to} GiB",
			},
		)
