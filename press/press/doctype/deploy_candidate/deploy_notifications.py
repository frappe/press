# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import sys
import typing
from textwrap import dedent
from typing import Optional, TypedDict

import frappe

if typing.TYPE_CHECKING:
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate


Details = TypedDict(
	"Details",
	{
		"title": Optional[str],
		"message": str,
		"traceback": Optional[str],
		"is_actionable": bool,
		"assistance_url": Optional[str],
	},
)

DOC_URLS = {
	"app-installation-issue": "https://frappecloud.com/docs/faq/app-installation-issue"
}


def create_build_failed_notification(dc: "DeployCandidate") -> None:
	"""
	Used to create press notifications on Build failures. If the notification
	is actionable then it will be displayed on the dashboard and will block
	further builds until the user has resolved it.
	"""

	if (exc := sys.exception()) is None:
		return

	details = get_details(dc, exc)
	doc_dict = {
		"doctype": "Press Notification",
		"team": dc.team,
		"type": "Bench Deploy",
		"document_type": dc.doctype,
		"document_name": dc.name,
		"class": "Error",
		**details,
	}
	doc = frappe.get_doc(doc_dict)
	doc.insert()
	frappe.db.commit()

	frappe.publish_realtime("press_notification", {"team": dc.team})


def get_details(dc: "DeployCandidate", exc: BaseException) -> "Details":
	tb = frappe.get_traceback(with_context=False)
	details: "Details" = dict(
		title=get_default_title(dc),
		message=get_default_message(dc),
		is_actionable=False,
		traceback=tb,
		assistance_url=None,
	)

	# Failure in Clone Repositories step, raise in app_release.py
	if "App installation token could not be fetched" in tb:
		update_with_github_token_error(details, dc, exc)

	# Failure in Clone Repositories step, raise in app_release.py
	elif "Repository could not be fetched" in tb:
		update_with_github_token_error(details, dc, exc, is_repo_not_found=True)
	return details


def update_with_github_token_error(
	details: "Details",
	dc: "DeployCandidate",
	exc: BaseException,
	is_repo_not_found: bool = False,
):
	if len(exc.args) > 1:
		app = exc.args[1]
	elif (failed_step := dc.get_first_step_of_given_status("Failure")) is not None:
		app = failed_step.step_slug

	if not app:
		return

	# Ensure that installation token is None
	if is_repo_not_found and not is_installation_token_none(dc, app):
		return

	details["is_actionable"] = True
	details["title"] += ": App access token could not be fetched"

	message = f"""
	{details['message']}

	App installation access token could not be fetched from GitHub API for the app <b>{app}</b>.
	To rectify this issue, please follow the steps mentioned in the link.
	""".strip()
	details["message"] = dedent(message)
	details["assistance_url"] = DOC_URLS["app-installation-issue"]


def is_installation_token_none(dc: "DeployCandidate", app: str) -> bool:
	from press.api.github import get_access_token

	matched = [a for a in dc.apps if a.app == app]
	if len(matched) == 0:
		return False

	dc_app = matched[0]
	installation_id = frappe.get_value(
		"App Source", dc_app.source, "github_installation_id"
	)

	try:
		return get_access_token(installation_id) is None
	except Exception:
		# Error is not actionable
		return False


def get_default_title(dc: "DeployCandidate") -> str:
	rg_title = frappe.get_value("Release Group", dc.group, "title")
	return f"<b>[{rg_title}]</b> Deploy Failed"


def get_default_message(dc: "DeployCandidate") -> str:
	failed_step = dc.get_first_step_of_given_status("Failure")
	if failed_step:
		return f"Image build failed at step <b>{failed_step.stage} - {failed_step.step}</b>."
	return "Image build failed."


def get_is_actionable(dc: "DeployCandidate", tb: str) -> bool:
	return False
