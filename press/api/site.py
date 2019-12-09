# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.password import get_decrypted_password


@frappe.whitelist()
def new(site):
	bench_name = frappe.get_all("Bench")[0].name
	bench = frappe.get_doc("Bench", bench_name)
	site_name = bench.new_site(site["name"]).name
	return {
		"name": site_name,
		"password": get_decrypted_password("Site", site_name, "password"),
	}

