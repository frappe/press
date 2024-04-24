# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors

from __future__ import unicode_literals
import frappe

from press.api.client import dashboard_whitelist


class TagHelpers:
	@dashboard_whitelist()
	def add_resource_tag(self, tag):
		team = frappe.local.team().name
		existing_tags = [row.tag_name for row in self.tags]
		if tag in existing_tags:
			return

		if not frappe.db.exists(
			"Press Tag", {"tag": tag, "doctype_name": self.doctype, "team": team}
		):
			tag_doc = frappe.new_doc(
				"Press Tag", tag=tag, doctype_name=self.doctype, team=team
			).insert()
		else:
			tag_doc = frappe.get_doc(
				"Press Tag",
				{"tag": tag, "doctype_name": self.doctype, "team": team},
			)

		self.append("tags", {"tag": tag_doc.name})
		self.save()

	@dashboard_whitelist()
	def remove_resource_tag(self, tag):
		self.tags = [row for row in self.tags if row.tag_name != tag]
		self.save()
