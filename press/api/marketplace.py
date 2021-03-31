# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from press.utils import get_current_team


@frappe.whitelist()
def signup():
	team = get_current_team(get_doc=True)
	team.app_publisher = True
	team.save()


@frappe.whitelist()
def apps():
	return frappe.get_list(
		"App",
		fields=[
			"title",
			"public",
			"url",
			"name",
			"team",
		],
		filters={"enabled": True, "team": get_current_team(), "frappe": False},
		order_by="creation desc",
	)


@frappe.whitelist()
def submit(app, values):
	values = frappe.parse_json(values)
	doc = frappe.new_doc("Marketplace App")

	fields = [
		"title",
		"description",
		"category",
		"image",
		"website",
		"privacy_policy",
		"documentation",
		"terms_of_service",
		"support",
	]
	for f in fields:
		doc.set(f, values[f])

	doc.name = frappe.scrub(doc.title)
	doc.frappe_app = app

	doc.insert()
	return doc.name


@frappe.whitelist()
def update(app, values):
	values = frappe.parse_json(values)
	doc = frappe.get_doc("Marketplace App", app)

	fields = [
		"title",
		"description",
		"category",
		"image",
		"website",
		"privacy_policy",
		"documentation",
		"terms_of_service",
		"support",
	]
	for f in fields:
		doc.set(f, values[f])

	doc.save()


@frappe.whitelist()
def categories():
	return frappe.db.get_all(
		"Marketplace App Category", fields="title as label, name as value"
	)


@frappe.whitelist()
def get(app):
	if frappe.db.exists("Marketplace App", {"frappe_app": app}):
		return frappe.get_doc("Marketplace App", {"frappe_app": app})
