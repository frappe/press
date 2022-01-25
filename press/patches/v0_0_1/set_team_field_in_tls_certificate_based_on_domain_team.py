# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "site_domain")
	frappe.reload_doc("press", "doctype", "tls_certificate")
	certificates = frappe.get_all(
		"TLS Certificate", ["name", "domain"], {"wildcard": False}
	)
	for certificate in certificates:
		team = frappe.db.get_value("Site Domain", certificate.domain, "team")
		frappe.db.set_value("TLS Certificate", certificate.name, "team", team)
