# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MarketplaceAppFeedback(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app_installed_on: DF.Datetime
		app_lifespan: DF.Duration
		feedback: DF.LongText
		marketplace_app: DF.Link
		site: DF.Link
		team: DF.Link
		team_created_on: DF.Datetime
	# end: auto-generated types

	pass


def collect_app_uninstall_feedback(app: str, feedback: str, site: str) -> None:
	"""
	Collect feedback when an app is uninstalled
	"""

	from press.utils import get_current_team

	if not app or not feedback or not site:
		return

	marketplace_app = frappe.db.get_value("Marketplace App", {"app": app}, "name")
	if not marketplace_app:
		return

	team = get_current_team()
	team_created_on = frappe.db.get_value("Team", team, "creation")

	app_installed_on = frappe.db.get_value("Site App", {"app": app, "parent": site}, "creation")
	app_lifespan = frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), app_installed_on)

	frappe.get_doc(
		{
			"doctype": "Marketplace App Feedback",
			"marketplace_app": marketplace_app,
			"feedback": feedback,
			"site": site,
			"team": team,
			"team_created_on": team_created_on,
			"app_installed_on": app_installed_on,
			"app_lifespan": app_lifespan,
		}
	).insert(ignore_permissions=True)
