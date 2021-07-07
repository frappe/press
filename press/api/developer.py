# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.utils import get_current_team


@frappe.whitelist()
def get_apps():
	"""Return list of apps developed by the current team"""
	team = get_current_team()
	apps = frappe.get_all(
		"Marketplace App",
		fields=["name", "title", "image", "app", "status", "description"],
		filters={"team": team},
	)

	return apps


@frappe.whitelist()
def get_app(name):
	"""Return the `Marketplace App` document with name"""
	app = frappe.get_doc("Marketplace App", name)
	return app


@frappe.whitelist()
def update_app_image():
	app_name = frappe.form_dict.docname
	_file = frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": "Marketplace App",
			"attached_to_name": app_name,
			"attached_to_field": "image",
			"folder": "Home/Attachments",
			"file_name": frappe.local.uploaded_filename,
			"is_private": 0,
			"content": frappe.local.uploaded_file,
		}
	)
	_file.save(ignore_permissions=True)
	file_url = _file.file_url
	frappe.db.set_value("Marketplace App", app_name, "image", file_url)

	return file_url


@frappe.whitelist()
def update_app_profile(name, title, category):
	app = frappe.get_doc("Marketplace App", name)
	app.title = title
	app.category = category
	app.save(ignore_permissions=True)
	return app


@frappe.whitelist()
def update_app_links(name, links):
	app = frappe.get_doc("Marketplace App", name)
	app.update(links)
	app.save(ignore_permissions=True)


@frappe.whitelist()
def categories():
	categories = frappe.get_all("Marketplace App Category", pluck="name")
	return categories
