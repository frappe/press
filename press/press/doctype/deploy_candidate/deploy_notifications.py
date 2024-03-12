# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
import typing

if typing.TYPE_CHECKING:
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate


def create_build_failed_notification(dc: "DeployCandidate", exc: Exception) -> None:
	"""
	Used to create press notifications on Build failures. If the notification
	is actionable then it will be displayed on the dashboard and will block
	further builds until the user has resolved it.
	"""

	doc_dict = {
		"doctype": "Press Notification",
		"team": dc.team,
		"type": "Bench Deploy",
		"document_type": dc.doctype,
		"document_name": dc.name,
		"title": get_title(dc, exc),
		"message": get_message(dc, exc),
		"traceback": get_traceback(dc, exc),
	}
	doc = frappe.get_doc(doc_dict)
	doc.insert()

	frappe.publish_realtime("press_notification", {"team": dc.team})


def get_title(dc: "DeployCandidate", exc: Exception) -> None | str:
	rg_title = frappe.get_value("Release Group", dc.group, "title")
	return f"Deploy failed for <b>{rg_title}</b>"


def get_message(dc: "DeployCandidate", exc: Exception) -> None | str:
	failed_step = dc.get_first_step_of_given_status("Failure")
	if failed_step:
		return f"Image build failed at step <b>{failed_step.stage} - {failed_step.step}</b>"
	return "Image build failed"


def get_is_actionable(dc: "DeployCandidate", exc: Exception) -> bool:
	return False


def get_traceback(dc: "DeployCandidate", exc: Exception) -> None | str:
	return None
