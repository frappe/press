# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import typing
from textwrap import dedent
from typing import Optional, TypedDict

import frappe
import frappe.utils

if typing.TYPE_CHECKING:
	from frappe import Document
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate

"""
Used to create notifications if the Deploy error is something that can
be handled by the user.

Ref: https://github.com/frappe/press/pull/1544

To handle an error:
1. Create a doc page that helps the user get out of it under: frappecloud.com/docs/common-issues
2. Check if the error is the known/expected one in `get_details`.
3. Update the details object with the correct values.
"""

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
	"app-installation-issue": "https://frappecloud.com/docs/faq/app-installation-issue",
	"invalid-pyproject-file": "https://frappecloud.com/docs/common-issues/invalid-pyprojecttoml-file",
	"incompatible-node-version": "https://frappecloud.com/docs/common-issues/incompatible-node-version",
}


def create_build_failed_notification(
	dc: "DeployCandidate", exc: "BaseException"
) -> bool:
	"""
	Used to create press notifications on Build failures. If the notification
	is actionable then it will be displayed on the dashboard and will block
	further builds until the user has resolved it.

	Returns if build failure is_actionable
	"""

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

	frappe.publish_realtime(
		"press_notification", doctype="Press Notification", message={"team": dc.team}
	)

	return details["is_actionable"]


def get_details(dc: "DeployCandidate", exc: BaseException) -> "Details":
	tb = frappe.get_traceback(with_context=False)
	details: "Details" = dict(
		title=get_default_title(dc),
		message=get_default_message(dc),
		is_actionable=False,
		traceback=tb,
		assistance_url=None,
	)

	"""
	In the conditionals below:
	- check if the error is a known one
	- set the title, message, is_actionable, assistance_url fields
	- ensure that no error is thrown
	"""

	# Failure in Clone Repositories step, raise in app_release.py
	if "App installation token could not be fetched" in tb:
		update_with_github_token_error(details, dc, exc)

	# Failure in Clone Repositories step, raise in app_release.py
	elif "Repository could not be fetched" in tb:
		update_with_github_token_error(details, dc, exc, is_repo_not_found=True)

	# Pyproject file could not be parsed by tomllib
	elif "App has invalid pyproject.toml file" in tb:
		update_with_invalid_pyproject_error(details, dc, exc)

	# Package JSON file could not be parsed by json.load
	elif "App has invalid package.json file" in tb:
		update_with_invalid_package_json_error(details, dc, exc)

	# Release Group Node version is incompatible with required version
	elif 'engine "node" is incompatible with this module' in dc.build_output:
		update_with_incompatible_node(details, dc)
	return details


def update_with_invalid_pyproject_error(
	details: "Details",
	dc: "DeployCandidate",
	exc: "BaseException",
):
	if len(exc.args) <= 1 or not (app := exc.args[1]):
		return

	build_step = get_ct_row(dc, app, "build_steps", "step_slug")
	app_name = build_step.step

	details["is_actionable"] = True
	details["title"] = f"{app_name} has an invalid pyproject.toml file"
	message = f"""
	<p>The <b>pyproject.toml</b> file in the <b>{app_name}</b> repository could not be
	decoded by <code>tomllib</code> due to syntax errors.</p>

	<p>To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	""".strip()
	details["message"] = dedent(message)
	details["assistance_url"] = DOC_URLS["invalid-pyproject-file"]


def update_with_invalid_package_json_error(
	details: "Details",
	dc: "DeployCandidate",
	exc: "BaseException",
):
	if len(exc.args) <= 1 or not (app := exc.args[1]):
		return

	build_step = get_ct_row(dc, app, "build_steps", "step_slug")
	app_name = build_step.step

	loc_str = ""
	if len(exc.args) >= 2 and isinstance(exc.args[2], str):
		loc_str = f"<p>File was found at path <b>{exc.args[2]}</b>.</p>"

	details["is_actionable"] = True
	details["title"] = f"{app_name} has an invalid package.json file"
	message = f"""
	<p>The <b>package.json</b> file in the <b>{app_name}</b> repository could not be
	decoded by <code>json.load</code>.</p>
	{loc_str}

	<p>To rectify this issue, please fix the <b>pyproject.json</b> file.</p>
	""".strip()
	details["message"] = dedent(message)


def update_with_github_token_error(
	details: "Details",
	dc: "DeployCandidate",
	exc: BaseException,
	is_repo_not_found: bool = False,
):
	if len(exc.args) > 1:
		app = exc.args[1]
	elif (failed_step := dc.get_first_step("status", "Failure")) is not None:
		app = failed_step.step_slug

	if not app:
		return

	# Ensure that installation token is None
	if is_repo_not_found and not is_installation_token_none(dc, app):
		return

	details["is_actionable"] = True
	details["title"] = "App access token could not be fetched"

	build_step = get_ct_row(dc, app, "build_steps", "step_slug")
	if not build_step:
		return

	app_name = build_step.step
	message = f"""
	<p>{details['message']}</p>

	<p><b>{app_name}</b> installation access token could not be fetched from GitHub.
	To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	""".strip()
	details["message"] = dedent(message)
	details["assistance_url"] = DOC_URLS["app-installation-issue"]


def update_with_incompatible_node(
	details: "Details",
	dc: "DeployCandidate",
) -> None:
	# Example line:
	# `#60 5.030 error customization_forms@1.0.0: The engine "node" is incompatible with this module. Expected version ">=18.0.0". Got "16.16.0"`
	line = get_build_output_line(dc, '"node" is incompatible with this module')
	app = get_app_from_incompatible_build_output_line(line)
	version = get_version_from_incompatible_build_output_line(line)

	details["is_actionable"] = True
	details["title"] = "Incompatible Node version"
	message = f"""
	<p>{details['message']}</p>

	<p><b>{app}</b> installation failed due to incompatible Node versions. {version}
	Please set the correct Node Version on your Bench.</p>

	<p>To rectify this issue, please follow the the steps mentioned in <i>Help</i>.</p>
	""".strip()
	details["message"] = dedent(message)
	details["assistance_url"] = DOC_URLS["incompatible-node-version"]

	# Traceback is not pertinent to issue
	details["traceback"] = None


def get_build_output_line(dc: "DeployCandidate", needle: str):
	for line in dc.build_output.split("\n"):
		if needle in line:
			return line
	return ""


def get_version_from_incompatible_build_output_line(line: str):
	if "Expected" not in line:
		return ""

	idx = line.index("Expected")
	return line[idx:] + "."


def get_app_from_incompatible_build_output_line(line: str):
	splits = line.split()
	if "error" not in splits:
		return ""

	idx = splits.index("error") + 1
	if len(splits) <= idx:
		return ""

	return splits[idx][:-1].split("@")[0]


def is_installation_token_none(dc: "DeployCandidate", app: str) -> bool:
	from press.api.github import get_access_token

	dc_app = get_ct_row(dc, app, "apps", "app")
	if dc_app is None:
		return False

	installation_id = frappe.get_value(
		"App Source", dc_app.source, "github_installation_id"
	)

	try:
		return get_access_token(installation_id) is None
	except Exception:
		# Error is not actionable
		return False


def get_default_title(dc: "DeployCandidate") -> str:
	return "Build Failed"


def get_default_message(dc: "DeployCandidate") -> str:
	failed_step = dc.get_first_step("status", "Failure")
	if failed_step:
		return f"Image build failed at step <b>{failed_step.stage} - {failed_step.step}</b>."
	return "Image build failed."


def get_is_actionable(dc: "DeployCandidate", tb: str) -> bool:
	return False


def get_ct_row(
	dc: "DeployCandidate",
	match_value: str,
	field: str,
	ct_field: str,
) -> Optional["Document"]:
	ct = dc.get(field)
	if not ct:
		return

	for row in ct:
		if row.get(ct_field) == match_value:
			return row
