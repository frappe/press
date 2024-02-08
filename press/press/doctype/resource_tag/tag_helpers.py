# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors

from __future__ import unicode_literals
import frappe


class TagHelpers:
	def __new__(self, *args, **kwargs):
		self.dashboard_actions += ["add_resource_tag", "remove_resource_tag"]
		return super(TagHelpers, self).__new__(self)

	@frappe.whitelist()
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

	@frappe.whitelist()
	def remove_resource_tag(self, tag):
		self.tags = [row for row in self.tags if row.tag_name != tag]
		self.save()
