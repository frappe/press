# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from press.utils import log_error


class Deploy(Document):
	def after_insert(self):
		self.create_benches()

	def create_benches(self):
		for bench in self.benches:
			new = frappe.get_doc(
				{
					"doctype": "Bench",
					"name": bench.bench_name,
					"server": bench.server,
					"group": self.group,
					"candidate": self.candidate,
				}
			).insert()
			bench.bench = new.name
			create_deploy_candidate_differences(new)


def create_deploy_candidate_differences(bench):
	group = bench.group
	destination = bench.candidate
	destination_creation = frappe.db.get_value("Deploy Candidate", destination, "creation")
	benches = frappe.get_all(
		"Bench",
		fields="candidate",
		filters={
			"server": bench.server,
			"status": "Active",
			"group": group,
			"candidate": ("!=", destination),
		},
	)
	candidates = list(set(b.candidate for b in benches))
	for source in candidates:
		try:
			source_creation = frappe.db.get_value("Deploy Candidate", source, "creation")
			if source_creation < destination_creation:
				frappe.get_doc(
					{
						"doctype": "Deploy Candidate Difference",
						"group": group,
						"source": source,
						"destination": destination,
					}
				).insert()
		except Exception:
			log_error(
				"Deploy Candidate Differnce Creation Error",
				bench=bench.as_dict(),
				candidates=candidates,
				source=source,
			)
