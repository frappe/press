# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from press.utils import log_error


class DeployCandidate(Document):
	def after_insert(self):
		return

	def create_deploy(self):
		try:
			deploy = frappe.db.exists("Deploy", {"group": self.group, "candidate": self.name})
			if deploy:
				return

			deployed_benches = frappe.get_all(
				"Bench", fields=["server"], filters={"group": self.group, "status": "Active"}
			)
			servers = list(set(bench.server for bench in deployed_benches))
			benches = []
			domain = frappe.db.get_single_value("Press Settings", "domain")
			for server in servers:
				server_name = server.replace(f".{domain}", "")
				bench_name = f"bench-{self.group.replace(' ', '-').lower()}-{server_name}"
				bench_name = append_number_if_name_exists("Bench", bench_name, separator="-")
				benches.append({"server": server, "bench_name": bench_name})
				if benches:
					deploy_doc = frappe.get_doc(
						{
							"doctype": "Deploy",
							"group": self.group,
							"candidate": self.name,
							"benches": benches,
						}
					)
					deploy_doc.insert()
		except Exception:
			log_error("Deploy Creation Error", candidate=self.name)
