# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe
from tqdm import tqdm


def execute():
	frappe.reload_doc("press", "doctype", "organization_member")
	frappe.reload_doc("press", "doctype", "organization")
	teams = frappe.get_all("Team", "*")
	for team in tqdm(teams):
		try:
			organization = team
			organization["doctype"] = "Organization"
			for member in frappe.get_all("Team Member", {"parent": team["name"]}, pluck="user"):
				organization.setdefault("members", []).append({"user": member})

			frappe.get_doc(organization).insert()
		except Exception as e:
			print("Couldn't create Organization from Team", team.name, e)
