# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe

no_cache = True


def get_context(context):
	app = frappe.get_doc("Marketplace App", frappe.form_dict.app)
	context.app = app
	if app.category:
		context.category = frappe.get_doc("Marketplace App Category", app.category)

	groups = frappe.get_all(
		"Release Group Frappe App", fields=["parent as name"], filters={"app": app.frappe_app}
	)
	enabled_groups = []
	for group in groups:
		group_doc = frappe.get_doc("Release Group", group.name)
		if not group_doc.enabled:
			continue
		frappe_app = frappe.get_all(
			"Frappe App",
			fields=["name", "scrubbed", "branch", "url"],
			filters={"name": ("in", [row.app for row in group_doc.apps]), "frappe": True},
		)[0]
		group["frappe"] = frappe_app
		enabled_groups.append(group)

	context.supported_versions = enabled_groups
