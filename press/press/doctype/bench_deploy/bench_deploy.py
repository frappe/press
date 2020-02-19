# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class BenchDeploy(Document):
	def validate(self):
		# TODO: Sane naming
		if not self.target_bench_name:
			self.target_bench_name = frappe.generate_hash(length=16)
		self.create_bench()

	def create_bench(self):
		bench = frappe.get_doc(
			{
				"doctype": "Bench",
				"name": self.target_bench_name,
				"server": self.server,
				"candidate": self.candidate,
			}
		)
		bench.insert()
		self.target_bench = self.target_bench_name
		self.job = frappe.get_all(
			"Agent Job", filters={"job_type": "New Bench", "bench": self.target_bench}
		)[0].name


def process_bench_deploy_job_update(job):
	deploy = frappe.get_all(
		"Bench Deploy", fields=["name", "status"], filters={"job": job.name}
	)
	# New Bench Job might not be triggered from Bench Deploy doctype.
	if deploy:
		deploy = deploy[0]
		if job.status != deploy.status:
			frappe.db.set_value("Bench Deploy", deploy.name, "status", job.status)
