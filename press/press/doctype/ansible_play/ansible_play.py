# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from press.api.client import is_owned_by_team
from press.utils import poly_get_doctype


class AnsiblePlay(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		changed: DF.Int
		duration: DF.Time | None
		end: DF.Datetime | None
		failures: DF.Int
		ignored: DF.Int
		ok: DF.Int
		play: DF.Data
		playbook: DF.Data
		rescued: DF.Int
		server: DF.DynamicLink
		server_type: DF.Link
		skipped: DF.Int
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		unreachable: DF.Int
		variables: DF.Code
	# end: auto-generated types

	dashboard_fields = [
		"name",
		"creation",
		"status",
		"start",
		"end",
		"duration",
		"server",
		"play",
	]

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		server = cstr(filters.get("server", ""))

		if not server:
			frappe.throw("Not permitted", frappe.PermissionError)

		servers = frappe.parse_json(server.replace("'", '"'))[1]

		for server in servers:
			doctype = poly_get_doctype(["Server", "Database Server"], server)
			is_owned_by_team(doctype, server, raise_exception=True)

		results = query.run(as_dict=1)
		return results

	def get_doc(self, doc):
		doc["tasks"] = frappe.get_all(
			"Ansible Task",
			filters={"play": self.name},
			fields=["task", "status", "start", "end", "duration"],
			order_by="creation",
		)

		return doc

	def on_trash(self):
		frappe.db.delete("Ansible Task", {"play": self.name})
