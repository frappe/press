# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from press.api.site import protected
from press.utils import get_current_team


@frappe.whitelist()
def all():
	sites = frappe.get_list(
		"Site",
		fields=["count(1) as count", "status"],
		order_by="creation desc",
		group_by="status",
	)
	return {"sites": sites}


@frappe.whitelist()
@protected(["Site", "Release Group", "Server", "Database Server"])
def create_new_tag(name, doctype, tag):
	tag = frappe.get_doc(
		{
			"doctype": "Press Tag",
			"doctype_name": doctype,
			"team": get_current_team(),
			"tag": tag,
		}
	).insert(ignore_permissions=True)
	doc = frappe.get_doc(doctype, name).append("tags", {"tag": tag})
	doc.save()
	return tag


@frappe.whitelist()
@protected(["Site", "Release Group", "Server", "Database Server"])
def add_tag(name, doctype, tag):
	doc = frappe.get_doc(doctype, name)
	doc.append("tags", {"tag": tag})
	doc.save()
	return tag


@frappe.whitelist()
@protected(["Site", "Release Group", "Server", "Database Server"])
def remove_tag(name, doctype, tag):
	doc = frappe.get_doc(doctype, name)
	for resource_tag in doc.tags:
		if resource_tag.tag == tag:
			doc.tags.remove(resource_tag)
			doc.save()
			return tag
