# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe
from tqdm import tqdm


def execute():
	links = frappe.get_all(
		"Dynamic Link",
		["name", "parent", "link_name"],
		{"parenttype": "Address", "link_doctype": "Team"},
	)
	for link in tqdm(links):
		try:
			doc = frappe.get_doc("Dynamic Link", link.name)
			doc.name = None
			doc.link_doctype = "Org"
			doc.db_insert()
		except Exception as e:
			print("Couldn't link Addres", link.parent, "to Org", link.link_name, e)
