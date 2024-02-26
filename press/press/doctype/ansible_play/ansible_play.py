# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import cstr

from press.api.client import is_owned_by_team
from press.utils import poly_get_doctype


class AnsiblePlay(Document):
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
