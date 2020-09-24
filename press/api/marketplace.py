# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def publish(app, values):
	values = frappe.parse_json(values)
	doc = frappe.new_doc("Marketplace App")
	doc.frappe_app = app
	doc.title = values.title
	doc.name = frappe.scrub(doc.title)
	doc.description = values.description
	doc.category = values.category
	doc.long_description = values.long_description
	doc.image = values.image
	doc.insert()
	return doc.name


@frappe.whitelist()
def categories():
	return frappe.db.get_all(
		"Marketplace App Category", fields="title as label, name as value"
	)


@frappe.whitelist()
def get(app):
	if frappe.db.exists("Marketplace App", {"frappe_app": app}):
		return frappe.get_doc("Marketplace App", {"frappe_app": app})
