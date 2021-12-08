import frappe
from frappe.utils import update_progress_bar


def execute():
	frappe.reload_doc("press", "doctype", "team")

	teams = frappe.db.get_all(
		"Team", filters={"referrer_id": ("is", "not set")}, pluck="name"
	)

	total_teams = len(teams)
	for i, team in enumerate(teams):
		update_progress_bar("Updating team", i, total_teams)
		team = frappe.get_doc("Team", team)
		team.set_referrer_id()
		team.db_set("referrer_id", team.referrer_id, update_modified=False)
