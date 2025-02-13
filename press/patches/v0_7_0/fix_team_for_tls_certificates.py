# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from tqdm import tqdm


def execute():
	site_domains = frappe.get_all("Site Domain", fields=["tls_certificate", "team"])

	for domain in tqdm(site_domains):
		frappe.db.set_value(
			"TLS Certificate", domain["tls_certificate"], "team", domain["team"], update_modified=False
		)
