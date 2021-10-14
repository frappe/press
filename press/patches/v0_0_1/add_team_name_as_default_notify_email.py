import frappe

frappe.reload_doctype("Team")
frappe.reload_doctype("Site")


def execute():
	"""Sets the value of notify email as team name"""
	teams = frappe.get_all("Team", pluck="name")
	for team in teams:
		frappe.db.set_value("Team", team, "notify_email", team)

	sites = frappe.get_all("Site", fields=["name", "team"])
	for site in sites:
		frappe.db.set_value("Site", site.name, "notify_email", site.team)
