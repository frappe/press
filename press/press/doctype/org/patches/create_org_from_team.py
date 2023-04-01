# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe
from tqdm import tqdm


def execute():
	frappe.reload_doc("press", "doctype", "org_member")
	frappe.reload_doc("press", "doctype", "org")
	teams = frappe.get_all("Team", "*")
	for team in tqdm(teams):
		try:
			org = team
			org["doctype"] = "Org"
			for member in frappe.get_all("Team Member", {"parent": team["name"]}, pluck="user"):
				org.setdefault("members", []).append({"user": member})

			frappe.get_doc(org).insert()
		except Exception as e:
			print("Couldn't create Org from Team", team.name, e)
