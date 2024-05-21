# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.utils import log_error
from frappe.model.naming import append_number_if_name_exists
from press.overrides import get_permission_query_conditions_for_doctype


class Deploy(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.deploy_bench.deploy_bench import DeployBench

		benches: DF.Table[DeployBench]
		candidate: DF.Link
		group: DF.Link
		staging: DF.Check
		team: DF.Link
	# end: auto-generated types

	def autoname(self):
		self.name = append_number_if_name_exists("Deploy", self.candidate, separator="-")

	def after_insert(self):
		self.create_benches()

	def create_benches(self):
		candidate = frappe.get_cached_doc("Deploy Candidate", self.candidate)
		environment_variables = [
			{"key": v.key, "value": v.value} for v in candidate.environment_variables
		]

		group = frappe.get_cached_doc("Release Group", self.group)
		mounts = [
			{
				"source": v.source,
				"destination": v.destination,
				"is_absolute_path": v.is_absolute_path,
			}
			for v in group.mounts
		]

		for bench in self.benches:
			new = frappe.get_doc(
				{
					"doctype": "Bench",
					"server": bench.server,
					"group": self.group,
					"candidate": self.candidate,
					"workers": 1,
					"staging": self.staging,
					"environment_variables": environment_variables,
					"mounts": mounts,
				}
			).insert()
			bench.bench = new.name

		frappe.enqueue(
			"press.press.doctype.deploy.deploy.create_deploy_candidate_differences",
			destination=self.candidate,
			enqueue_after_commit=True,
		)
		self.save()


def create_deploy_candidate_differences(destination):
	destination = frappe.get_cached_doc("Deploy Candidate", destination)
	group = destination.group
	destination_creation = destination.creation
	candidates = frappe.get_all(
		"Bench",
		pluck="candidate",
		filters={
			"status": ("!=", "Archived"),
			"group": group,
			"candidate": ("!=", destination.name),
		},
	)
	candidates = list(set(candidates))
	for source in candidates:
		try:
			source_creation = frappe.db.get_value("Deploy Candidate", source, "creation")
			if source_creation < destination_creation:
				if frappe.get_all(
					"Deploy Candidate Difference",
					filters={
						"group": group,
						"source": source,
						"destination": destination.name,
					},
					limit=1,
				):
					continue
				frappe.get_doc(
					{
						"doctype": "Deploy Candidate Difference",
						"group": group,
						"source": source,
						"destination": destination.name,
					}
				).insert()
				frappe.db.commit()
		except Exception:
			log_error(
				"Deploy Candidate Difference Creation Error",
				destination=destination,
				candidates=candidates,
				source=source,
			)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Deploy")
