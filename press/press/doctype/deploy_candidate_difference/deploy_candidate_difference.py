# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.core.utils import find
from press.overrides import get_permission_query_conditions_for_doctype


class DeployCandidateDifference(Document):
	def validate(self):
		if self.source == self.destination:
			frappe.throw(
				"Destination Candidate must be different from Source Candidate",
				frappe.ValidationError,
			)

		source_creation = frappe.db.get_value("Deploy Candidate", self.source, "creation")
		destination_creation = frappe.db.get_value(
			"Deploy Candidate", self.destination, "creation"
		)
		if source_creation > destination_creation:
			frappe.throw(
				"Destination Candidate must be created after Source Candidate",
				frappe.ValidationError,
			)

		if frappe.get_all(
			"Deploy Candidate Difference",
			filters={
				"group": self.group,
				"source": self.source,
				"destination": self.destination,
				"name": ("!=", self.name),
			},
		):
			frappe.throw(
				"Deploy Candidate Difference already exists for Release Group: {} "
				", Source Release: {} and Destination Release: {}".format(
					self.group, self.source, self.destination
				),
				frappe.ValidationError,
			)

		self.populate_apps_table()

	def populate_apps_table(self):
		source_candidate = frappe.get_doc("Deploy Candidate", self.source)
		destination_candidate = frappe.get_doc("Deploy Candidate", self.destination)
		for destination in destination_candidate.apps:
			source = find(source_candidate.apps, lambda x: x.app == destination.app)
			if not source or source.release == destination.release:
				continue
			differences = frappe.get_all(
				"App Release Difference",
				["name", "deploy_type"],
				{"source_release": source.release, "destination_release": destination.release},
				limit=1,
			)
			if not differences:
				difference = frappe.get_doc(
					{
						"doctype": "App Release Difference",
						"app": destination.app,
						"source": destination.source,
						"source_release": source.release,
						"destination_release": destination.release,
					}
				)
				difference.insert()
			else:
				difference = differences[0]
			self.append(
				"apps",
				{
					"app": destination.app,
					"destination_release": destination.release,
					"source_release": source.release,
					"difference": difference.name,
					"deploy_type": difference.deploy_type,
				},
			)

			if difference.deploy_type == "Migrate":
				self.deploy_type = "Migrate"


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Deploy Candidate Difference"
)
