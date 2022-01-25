# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("TLS Certificate")
	rename_field("TLS Certificate", "expiry", "expires_on")
	rename_field("TLS Certificate", "privkey", "private_key")
	rename_field("TLS Certificate", "fullchain", "full_chain")
	rename_field("TLS Certificate", "chain", "intermediate_chain")
