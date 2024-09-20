from __future__ import annotations

# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
import frappe


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

		notify_email = frappe.db.get_value("Team", app_doc.team, "notify_email")
		if notify_email and not (logo and desc and links and release):
			frappe.sendmail(
				subject=f"Marketplace App Review: {app_doc.title}",
				recipients=[notify_email],
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
