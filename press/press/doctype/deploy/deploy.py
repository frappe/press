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
	benches = frappe.get_all(
		"Bench",
		fields="candidate",
		filters={"server": bench.server, "name": ("!=", bench.name), "group": bench.group},
	)
	candidates = list(set(b.candidate for b in benches if b.candidate != bench.candidate))
	for candidate in candidates:
		try:
			frappe.get_doc(
				{
					"doctype": "Deploy Candidate Difference",
					"group": bench.group,
					"source": candidate,
					"destination": bench.candidate,
				}
			).insert()
		except Exception:
			log_error(
				"Deploy Candidate Differnce Creation Error",
				bench=bench.as_dict(),
				candidates=candidates,
				candidate=candidate,
			)
