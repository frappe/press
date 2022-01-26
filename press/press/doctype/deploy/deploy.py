# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.utils import log_error
from frappe.model.naming import append_number_if_name_exists
from press.overrides import get_permission_query_conditions_for_doctype


class Deploy(Document):
	def autoname(self):
		self.name = append_number_if_name_exists("Deploy", self.candidate, separator="-")

	def after_insert(self):
		self.create_benches()

	def create_benches(self):
		for bench in self.benches:
			new = frappe.get_doc(
				{
					"doctype": "Bench",
					"server": bench.server,
					"group": self.group,
					"candidate": self.candidate,
					"workers": 1,
					"staging": self.staging,
				}
			).insert()
			bench.bench = new.name

			frappe.enqueue(
				"press.press.doctype.deploy.deploy.create_deploy_candidate_differences",
				bench=new,
				enqueue_after_commit=True,
			)
		self.save()


def create_deploy_candidate_differences(bench):
	group = bench.group
	destination = bench.candidate
	destination_creation = frappe.db.get_value("Deploy Candidate", destination, "creation")
	benches = frappe.get_all(
		"Bench",
		fields="candidate",
		filters={
			"server": bench.server,
			"status": ("!=", "Archived"),
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


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Deploy")
