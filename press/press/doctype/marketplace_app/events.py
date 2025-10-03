# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.communication_info.communication_info import get_communication_info


def auto_review_for_missing_steps():
	for app in frappe.get_all(
		"Marketplace App",
		{
			"status": ("in", ["Draft", "Attention Required", "In Review"]),
			"stop_auto_review": False,
		},
		pluck="name",
	):
		app_doc = frappe.get_doc("Marketplace App", app)
		release = bool(frappe.db.exists("App Release Approval Request", {"app": app}))
		logo = bool(app_doc.image)
		desc = "Please add a short" not in app_doc.description
		links = bool(
			app_doc.website
			and app_doc.support
			and app_doc.documentation
			and app_doc.privacy_policy
			and app_doc.terms_of_service
		)

		recipients = get_communication_info("Email", "Marketplace", "Team", app_doc.team)
		if recipients and not (logo and desc and links and release):
			frappe.sendmail(
				subject=f"Marketplace App Review: {app_doc.title}",
				recipients=recipients,
				template="marketplace_auto_review",
				reference_doctype="Marketplace App",
				reference_name=app,
				args={
					"logo": logo,
					"links": links,
					"desc": desc,
					"release": release,
					"review_page_link": f"{frappe.local.site}/dashboard/marketplace/apps/{app}/review",
				},
			)
