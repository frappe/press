# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from press.press.doctype.nfs_server.nfs_server import NFSServer


class MountEnabledServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		server: DF.Link
		share_file_system: DF.Check
		use_file_system_of_server: DF.Link | None
	# end: auto-generated types

	def after_insert(self):
		nfs_server: NFSServer = frappe.get_doc("NFS Server", self.parent)
		private_ip = frappe.db.get_value("Server", self.server, "private_ip")
		nfs_server.agent.post(
			"/nfs/exports",
			data={
				"server": self.server,
				"private_ip": private_ip,
				"share_file_system": self.share_file_system,
				"use_file_system_of_server": self.use_file_system_of_server,
			},
		)

	def on_delete(self): ...
