# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "root_domain")
	press_settings = frappe.get_doc("Press Settings", "Press Settings")
	if (
		press_settings.domain
		and press_settings.aws_secret_access_key
		and not frappe.db.exists("Root Domain", press_settings.domain)
	):
		default_cluster = frappe.db.get_value("Cluster", {"default": True})
		frappe.get_doc(
			{
				"doctype": "Root Domain",
				"name": press_settings.domain,
				"default_cluster": default_cluster,
				"dns_provider": press_settings.dns_provider,
				"aws_access_key_id": press_settings.aws_access_key_id,
				"aws_secret_access_key": press_settings.get_password("aws_secret_access_key"),
			}
		).insert()
