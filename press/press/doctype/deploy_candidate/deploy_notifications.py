# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
import typing
from textwrap import dedent
from typing import Protocol, TypedDict

import frappe

from press.press.doctype.deploy_candidate.utils import (
	BuildValidationError,
	get_error_key,
)

"""
Used to create notifications if the Deploy error is something that can
be handled by the user.

Ref: https://github.com/frappe/press/pull/1544

To handle an error:
1. Create a doc page that helps the user get out of it under: docs.frappe.io/cloud/common-issues
2. Check if the error is the known/expected one in `get_details`.
3. Update the details object with the correct values.
"""


class Details(TypedDict):
	title: str | None
	message: str
	traceback: str | None
	is_actionable: bool
	assistance_url: str | None


# These strings are checked against the traceback or build_output
MatchStrings = str | list[str]

if typing.TYPE_CHECKING:
	from frappe import Document

	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_app.deploy_candidate_app import (
		DeployCandidateApp,
	)
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
	from press.press.doctype.deploy_candidate_build_step.deploy_candidate_build_step import (
		DeployCandidateBuildStep,
	)

	# TYPE_CHECKING guard for code below cause DeployCandidate
	# might cause circular import.
	class UserAddressableHandler(Protocol):
		def __call__(
			self,
			details: "Details",
			dc: "DeployCandidate",
			dcb: "DeployCandidateBuild",
			exc: BaseException,
		) -> bool:  # Return True if is_actionable
			...

	class WillFailChecker(Protocol):
		def __call__(self, old_dc: "DeployCandidate", new_dc: "DeployCandidate") -> None: ...

	UserAddressableHandlerTuple = tuple[
		MatchStrings,
		UserAddressableHandler,
		WillFailChecker | None,
	]


DOC_URLS = {
	"app-installation-issue": "https://docs.frappe.io/cloud/faq/app-installation-issue",
	"invalid-pyproject-file": "https://docs.frappe.io/cloud/common-issues/invalid-pyprojecttoml-file",
	"incompatible-node-version": "https://docs.frappe.io/cloud/common-issues/incompatible-node-version",
	"incompatible-dependency-version": "https://docs.frappe.io/cloud/common-issues/incompatible-dependency-version",
	"incompatible-app-version": "https://docs.frappe.io/cloud/common-issues/incompatible-app-version",
	"required-app-not-found": "https://docs.frappe.io/cloud/common-issues/required-app-not-found",
	"debugging-app-installs-locally": "https://docs.frappe.io/cloud/common-issues/debugging-app-installs-locally",
	"vite-not-found": "https://docs.frappe.io/cloud/common-issues/vite-not-found",
	"invalid-project-structure": "https://docs.frappe.io/framework/user/en/tutorial/create-an-app#app-directory-structure",
	"frappe-not-found": "https://pip.pypa.io/en/stable/news/#v25-3",
	"no-python-dependency-file-found": "https://packaging.python.org/en/latest/guides/writing-pyproject-toml/",
}


def handlers():
	"""
	Returns list[UserAddressableHandlerTuple]

	Before adding anything here, view the type:
	`UserAddressableHandlerTuple`

	The first value of the tuple is `MatchStrings` which
	a list of strings (or a single string) which if they
	are present in the `traceback` or the `build_output`
	then then second value i.e. `UserAddressableHandler`
	is called.

	`UserAddressableHandler` is used to update the details
	used to create the Press Notification

	`UserAddressableHandler` can return False if it isn't
	user addressable, in this case the remaining handler
	tuple will be checked.

	Due to this order of the tuples matter.

	The third value is the `WillFailChecker` which is called
	when a new Deploy Candidate is to be made and the previous
	Deploy Candidate suffered a User Addressable Failure.

	The `WillFailChecker` is placed in proximity with
	notification handlers because that's where the error is
	evaluated and it's key stored on a Deploy Candidate
	as `error_key`.
	"""
	return [
		(
			"App installation token could not be fetched",
			update_with_app_not_fetchable,
			None,
		),
		(
			"Repository could not be fetched",
			update_with_app_not_fetchable,
			None,
		),
		(
			"No python dependency file found",
			update_with_no_python_dependency_file_error,
			check_if_app_updated,
		),
		(
			"App has invalid pyproject.toml file",
			update_with_invalid_pyproject_error,
			None,
		),
		(
			"App has invalid package.json file",
			update_with_invalid_package_json_error,
			None,
		),
		(
			'engine "node" is incompatible with this module',
			update_with_incompatible_node,
			check_incompatible_node,
		),
		(
			"Incompatible Node version found",
			update_with_incompatible_node,
			check_incompatible_node,
		),
		(
			"Incompatible Python version found",
			update_with_incompatible_python_prebuild,
			None,
		),
		(
			"Incompatible app version found",
			update_with_incompatible_app_prebuild,
			None,
		),
		(
			"Invalid release found",
			update_with_invalid_release_prebuild,
			None,
		),
		(
			"Required app not found",
			update_with_required_app_not_found_prebuild,
			None,
		),
		(
			"ModuleNotFoundError: No module named 'frappe'",
			update_with_unsupported_init_file,
			check_if_app_updated,
		),
		(
			"Could not determine the package name. Checked pyproject.toml, setup.cfg, and setup.py.",
			update_with_installation_file_not_found,
			check_if_app_updated,
		),
		(
			"ModuleNotFoundError: No module named",
			update_with_module_not_found,
			check_if_app_updated,
		),
		(
			"ImportError: cannot import name",
			update_with_import_error,
			check_if_app_updated,
		),
		(
			"No matching distribution found for",
			update_with_dependency_not_found,
			check_if_app_updated,
		),
		(
			"[ERROR] [plugin vue]",
			update_with_vue_build_failed,
			check_if_app_updated,
		),
		(
			"[ERROR] [plugin frappe-vue-style]",
			update_with_vue_build_failed,
			check_if_app_updated,
		),
		(
			"vite: not found",
			update_with_vite_not_found,
			check_if_app_updated,
		),
		(
			"FileNotFoundError: [Errno 2] No such file or directory",
			update_with_file_not_found,
			check_if_app_updated,
		),
		(
			"minimum supported Python version is",
			update_with_incompatible_python,
			check_incompatible_python,
		),
		(
			"pip._vendor.packaging.version.InvalidVersion: Invalid version",
			update_with_error_on_pip_install,
			check_if_app_updated,
		),
		# Below three are catch all fallback handlers for `yarn build`,
		# `yarn install` and `pip install` errors originating due to
		# issues in an app.
		#
		# They should always be at the end.
		(
			"subprocess.CalledProcessError: Command 'bench build --app",
			update_with_yarn_build_failed,
			check_if_app_updated,
		),
		(
			"This error originates from a subprocess, and is likely not a problem with pip",
			update_with_error_on_pip_install,
			check_if_app_updated,
		),
		(
			"ERROR: yarn install --check-files",
			update_with_yarn_install_failed,
			check_if_app_updated,
		),
		# Catch app install failures in cases of malformed package structure etc, etc.
		# https://github.com/frappe/bench/pull/1665/files
		(
			"Error occurred during app install",
			update_with_invalid_app_structure,
			None,
		),
		(
			"`frappe` package is installed from PyPI, which isn't supported",
			update_with_frappe_installed_from_pypi,
			None,
		),
	]


def create_build_warning_notification(
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	title: str,
	message: str,
) -> bool:
	"""Create a warning notification for build"""
	warning_details = {"title": title, "message": message}
	doc_dict = {
		"doctype": "Press Notification",
		"team": dc.team,
		"type": "Bench Deploy",
		"document_type": dcb.doctype,
		"document_name": dcb.name,
		"class": "Warning",
		**warning_details,
	}
	doc = frappe.get_doc(doc_dict)
	doc.insert()
	frappe.db.commit()

	frappe.publish_realtime("press_notification", doctype="Press Notification", message={"team": dc.team})

	return True


def create_build_failed_notification(
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException | None,
) -> bool:
	"""
	Used to create press notifications on Build failures. If the notification
	is actionable then it will be displayed on the dashboard and will block
	further builds until the user has resolved it.

	Returns True if build failure is_actionable
	"""
	if exc is None:
		# Exception is not passed if called from
		# build agent job update handler
		exc = Exception("PLACEHOLDER_EXCEPTION")

	details = get_details(deploy_candidate=dc, deploy_candidate_build=dcb, exc=exc)
	doc_dict = {
		"doctype": "Press Notification",
		"team": dc.team,
		"type": "Bench Deploy",
		"document_type": dcb.doctype,
		"document_name": dcb.name,
		"class": "Error",
		**details,
	}
	doc = frappe.get_doc(doc_dict)
	doc.insert()
	frappe.db.commit()

	frappe.publish_realtime("press_notification", doctype="Press Notification", message={"team": dc.team})

	return details["is_actionable"]


def get_details(
	deploy_candidate: "DeployCandidate", deploy_candidate_build: "DeployCandidateBuild", exc: BaseException
) -> "Details":
	tb = frappe.get_traceback(with_context=False)
	default_title = get_default_title(deploy_candidate)
	default_message = get_default_message(deploy_candidate_build)

	details: "Details" = dict(
		title=default_title,
		message=default_message,
		traceback=tb,
		is_actionable=False,
		assistance_url=None,
	)

	for strs, handler, _ in handlers():
		if isinstance(strs, str):
			strs = [strs]

		if not (is_match := all(s in tb for s in strs)):
			is_match = all(s in deploy_candidate_build.build_output for s in strs)

		if not is_match:
			continue

		if handler(details, deploy_candidate, deploy_candidate_build, exc):
			details["is_actionable"] = True
			deploy_candidate_build.error_key = get_error_key(strs)
			break

		details["title"] = default_title
		details["message"] = default_message
		details["traceback"] = tb
		details["is_actionable"] = False
		details["assistance_url"] = None

	return details


def update_with_frappe_installed_from_pypi(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	details["title"] = (
		"[Action Required] App installation failed due to 'frappe' package being installed from PyPI"
	)

	message = """
	<p><strong>Installation Failed:</strong> Your custom app's installation is failing because the <code>frappe</code> package is installed from PyPI.
	This setup is not supported and is preventing the installation from completing.</p>

	<p>Please remove <code>frappe</code> from your app's <code>requirements.txt</code> or <code>pyproject.toml</code> file to proceed.</p>
	"""

	details["message"] = fmt(message)
	return True


def update_with_unsupported_init_file(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	details["title"] = "[Action Required] App installation failed due to unsupported code in __init__.py"

	message = """
    <p><strong>Installation Failed:</strong> Your custom app's <code>__init__.py</code> file contains an import statement for <code>frappe</code>.
    This behavior is no longer supported and is preventing the installation from completing.</p>

    <p>Please remove any <code>frappe</code> import statements from your <code>__init__.py</code> file to proceed.</p>

    <p><strong>Temporary Workarounds:</strong></p>
    <ul>
        <li>Downgrade <strong>pip</strong> to version <strong>25.2</strong> in the <em>Bench Dependencies</em> tab.</li>
        <li>Upgrade Bench to version <strong>5.26.0</strong> from the same tab.</li>
    </ul>

    <p>For additional details, you may refer to the
        <a href="https://pip.pypa.io/en/stable/news/" target="_blank">pip release notes</a>.
    </p>
	"""

	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["frappe-not-found"]
	return True


def update_with_vue_build_failed(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	failed_step = get_failed_step(dcb)
	app_name = None

	details["title"] = "App installation failed due to errors in frontend code"

	if failed_step.stage_slug == "apps":
		app_name = failed_step.step
		message = f"""
		<p><b>{app_name}</b> installation has failed due to errors in its
		frontend (Vue.js) code.</p>

		<p>Please view the failing step <b>{failed_step.stage} - {failed_step.step}</b>
		output to debug and fix the error before retrying build.</p>
		"""
	else:
		message = """
		<p>App installation has failed due to errors in its frontend (Vue.js) code.</p>

		<p>Please view the build output to debug and fix the error before retrying
		build.</p>
		"""

	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["debugging-app-installs-locally"]
	return True


def update_with_import_error(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	failed_step = get_failed_step(dcb)
	app_name = None

	details["title"] = "App installation failed due to invalid import"

	lines = [line for line in dcb.build_output.split("\n") if "ImportError: cannot import name" in line]
	invalid_import = None
	if len(lines) > 1 and len(parts := lines[0].split("From")) > 1:
		imported = parts[0].strip().split(" ")[-1][1:-1]
		module = parts[1].strip().split(" ")[0][1:-1]
		invalid_import = f"{imported} from {module}"

	if failed_step.stage_slug == "apps" and invalid_import:
		app_name = failed_step.step
		message = f"""
		<p><b>{app_name}</b> installation has failed due to invalid import
		<b>{invalid_import}</b>.</p>

		<p>Please ensure all Python dependencies are of the required
		versions.</p>

		<p>Please view the failing step <b>{failed_step.stage} - {failed_step.step}</b>
		output to debug and fix the error before retrying build.</p>
		"""
	else:
		message = """
		<p>App installation failed due to an invalid import.</p>

		<p>Please view the build output to debug and fix the error
		before retrying build.</p>
		"""

	details["assistance_url"] = DOC_URLS["debugging-app-installs-locally"]
	details["message"] = fmt(message)
	return True


def update_with_module_not_found(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	failed_step = get_failed_step(dcb)
	app_name = None

	details["title"] = "App installation failed due to missing module"

	lines = [line for line in dcb.build_output.split("\n") if "ModuleNotFoundError: No module named" in line]
	missing_module = None
	if len(lines) > 1:
		missing_module = lines[0].split(" ")[-1][1:-1]

	if failed_step.stage_slug == "apps" and missing_module:
		app_name = failed_step.step
		message = f"""
		<p><b>{app_name}</b> installation has failed due to imported module
		<b>{missing_module}</b> not being found.</p>

		<p>Please ensure all imported Frappe app dependencies have been added
		to your bench and all Python dependencies have been added to your app's
		<b>requirements.txt</b> or <b>pyproject.toml</b> file before retrying
		the build.</p>
		"""
	else:
		message = """
		<p>App installation failed due to an imported module not being found.</p>

		<p>Please view the failing step output to debug and fix the error
		before retrying build.</p>
		"""

	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["debugging-app-installs-locally"]
	return True


def update_with_dependency_not_found(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	failed_step = get_failed_step(dcb)
	app_name = None

	details["title"] = "App installation failed due to dependency not being found"

	lines = [line for line in dcb.build_output.split("\n") if "No matching distribution found for" in line]
	missing_dep = None
	if len(lines) > 1:
		missing_dep = lines[0].split(" ")[-1]

	if failed_step.stage_slug == "apps" and missing_dep:
		app_name = failed_step.step
		message = f"""
		<p><b>{app_name}</b> installation has failed due to dependency
		<b>{missing_dep}</b> not being found.</p>

		<p>Please specify a version of <b>{missing_dep}</b> installable by
		<b>pip</b>.</p>

		<p>Please view the failing step output for more info.</p>
		"""
	else:
		message = """
		<p>App installation failed due to pip not being able to find a
		distribution of a dependency in your app.</p>

		<p>Please view the build output to debug and fix the error before
		retrying build.</p>
		"""

	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["debugging-app-installs-locally"]
	return True


def update_with_error_on_pip_install(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	failed_step = get_failed_step(dcb)
	app_name = None

	details["title"] = "App installation failed due to errors"

	if failed_step.stage_slug == "apps":
		app_name = failed_step.step
		message = f"""
		<p>App setup for <b>{app_name}</b> using pip failed due to
		errors originating in the app.</p>

		<p>Please view the failing step <b>{failed_step.stage} - {failed_step.step}</b>
		output to debug and fix the error before retrying build.</p>
		"""
	else:
		message = """
		<p>App setup using pip failed due to errors originating in an
		app on your Bench.</p>

		<p>Please view the build output to debug and fix the error before retrying
		build.</p>
		"""

	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["debugging-app-installs-locally"]
	return True


def update_with_no_python_dependency_file_error(
	details: "Details", dc: "DeployCandidate", dcb: "DeployCandidateBuild", exc: BaseException
):
	"No python dependency file found"
	app_name = exc.args[-1]

	details["title"] = "Validation Failed: No python dependency file found"
	message = f"""
	<p><b>{app_name}</b> does not have a python dependency file.

	Please add a <code>pyproject.toml</code> file.</p>

	<p>To rectify this issue, please follow the the steps mentioned in <i>Help</i>.</p>
	"""
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["no-python-dependency-file-found"]

	details["traceback"] = None
	return True


def update_with_invalid_pyproject_error(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	if len(exc.args) <= 1 or not (app := exc.args[1]):
		return False

	build_step: DeployCandidateBuildStep = get_ct_row(dcb, app, "build_steps", "step_slug")
	app_name = build_step.step

	details["title"] = "Invalid pyproject.toml file found"
	message = f"""
	<p>The <b>pyproject.toml</b> file in the <b>{app_name}</b> repository could not be
	decoded by <code>tomllib</code> due to syntax errors.</p>

	<p>To rectify this issue, please follow the steps mentioned in <i>Help</i>.</p>
	"""
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["invalid-pyproject-file"]
	return True


def update_with_invalid_app_structure(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	if len(exc.args) <= 1 or not (app := exc.args[1]):
		return False

	build_step: DeployCandidateBuildStep = get_ct_row(dcb, app, "build_steps", "step_slug")
	app_name = build_step.step

	details["title"] = "App Installation Failed"
	message = f"""
	<p>The installation of <b>{app_name}</b> failed because its structure does not
	conform to the expected Python package format.</p>

	<p>Please ensure that the repository contains a valid <b>setup.py</b> or
	<b>pyproject.toml</b> file and that all dependencies are correctly defined.</p>

	<p>For further guidance, refer to the <i>Help</i> documentation.</p>
	"""
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["invalid-project-structure"]
	return True


def update_with_invalid_package_json_error(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	if len(exc.args) <= 1 or not (app := exc.args[1]):
		return False

	build_step: DeployCandidateBuildStep = get_ct_row(dcb, app, "build_steps", "step_slug")
	app_name = build_step.step

	loc_str = ""
	if len(exc.args) >= 2 and isinstance(exc.args[2], str):
		loc_str = f"<p>File was found at path <b>{exc.args[2]}</b>.</p>"

	details["title"] = "Invalid package.json file found"
	message = f"""
	<p>The <b>package.json</b> file in the <b>{app_name}</b> repository could not be
	decoded by <code>json.load</code>.</p>
	{loc_str}

	<p>To rectify this issue, please fix the <b>pyproject.json</b> file.</p>
	"""
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["debugging-app-installs-locally"]
	return True


def update_with_app_not_fetchable(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	failed_step = get_failed_step(dcb)

	details["title"] = "App could not be fetched"
	if failed_step.stage_slug == "apps":
		app_name = failed_step.step
		message = f"""
		<p><b>{app_name}</b> could not be fetched from GitHub.</p>

		<p>This may have been due to an invalid installation id or due
		to an invalid repository URL.</p>

		<p>For a possible solutions, please follow the steps mentioned
		in <i>Help</i>.</p>
		"""
	else:
		message = """
		<p>App could not be fetched from GitHub.</p>

		<p>This may have been due to an invalid installation id or due
		to an invalid repository URL.</p>

		<p>For a possible solutions, please follow the steps mentioned
		in <i>Help</i>.</p>
		"""

	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["app-installation-issue"]
	return True


def update_with_incompatible_node(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
) -> bool:
	# Example line:
	# `#60 5.030 error customization_forms@1.0.0: The engine "node" is incompatible with this module. Expected version ">=18.0.0". Got "16.16.0"`
	if line := get_build_output_line(dcb, '"node" is incompatible with this module'):
		app = get_app_from_incompatible_build_output_line(line)
		version = ""
	elif len(exc.args) == 5:
		app = exc.args[1]
		version = f'Expected "{exc.args[3]}", found "{exc.args[2]}". '

	details["title"] = "Incompatible Node version"
	message = f"""
	<p>{details["message"]}</p>

	<p><b>{app}</b> installation failed due to incompatible Node versions. {version}
	Please set the correct Node Version on your Bench.</p>

	<p>To rectify this issue, please follow the the steps mentioned in <i>Help</i>.</p>
	"""
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["incompatible-node-version"]

	# Traceback is not pertinent to issue
	details["traceback"] = None
	return True


def check_incompatible_node(old_dcb: "DeployCandidateBuild", new_dc: "DeployCandidate") -> None:
	old_node = old_dcb.candidate.get_dependency_version("node")
	new_node = new_dc.get_dependency_version("node")

	if old_node != new_node:
		return

	frappe.throw(
		"Node version not updated since previous failing build.",
		BuildValidationError,
	)


def update_with_incompatible_python(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	details["title"] = "Incompatible Python version"
	message = """
	<p>App installation has failed due to the Python version on your Bench
	being incompatible. Please check build output for more details.</p>

	<p>To rectify this issue, please update the Python version on your bench.</p>

	<p>For reference, you can follow the steps mentioned in <i>Help</i>.</p>
	"""

	details["message"] = fmt(message)
	details["traceback"] = None
	details["assistance_url"] = DOC_URLS["incompatible-dependency-version"]
	return True


def check_incompatible_python(old_dcb: "DeployCandidateBuild", new_dc: "DeployCandidate") -> None:
	old_node = old_dcb.candidate.get_dependency_version("python")
	new_node = new_dc.get_dependency_version("python")

	if old_node != new_node:
		return

	frappe.throw(
		"Python version not updated since previous failing build.",
		BuildValidationError,
	)


def update_with_incompatible_node_prebuild(
	details: "Details",
	dc: "DeployCandidate",
	exc: BaseException,
) -> bool:
	if len(exc.args) != 5:
		return False

	_, app, actual, expected, package_name = exc.args

	package_name_str = ""
	if isinstance(package_name, str):
		package_name_str = f"Version requirement comes from package <b>{package_name}</b>"

	details["title"] = "Validation Failed: Incompatible Node version"
	message = f"""
	<p><b>{app}</b> requires Node version <b>{expected}</b>, found version is <b>{actual}</b>.
	{package_name_str}

	Please set the correct Node version on your Bench.</p>

	<p>To rectify this issue, please follow the the steps mentioned in <i>Help</i>.</p>
	"""
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["incompatible-node-version"]

	# Traceback is not pertinent to issue
	details["traceback"] = None
	return True


def update_with_incompatible_python_prebuild(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
) -> bool:
	if len(exc.args) != 4:
		return False

	_, app, actual, expected = exc.args

	details["title"] = "Validation Failed: Incompatible Python version"
	message = f"""
	<p><b>{app}</b> requires Python version <b>{expected}</b>, found version is <b>{actual}</b>.
	Please set the correct Python version on your Bench.</p>

	<p>To rectify this issue, please follow the the steps mentioned in <i>Help</i>.</p>
	"""
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["incompatible-dependency-version"]

	# Traceback is not pertinent to issue
	details["traceback"] = None
	return True


def update_with_incompatible_app_prebuild(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
) -> bool:
	if len(exc.args) != 5:
		return False

	_, app, dep_app, actual, expected = exc.args

	details["title"] = "Validation Failed: Incompatible app version"

	message = f"""
	<p><b>{app}</b> depends on version <b>{expected}</b> of <b>{dep_app}</b>.
	Found version is <b>{actual}</b></p>

	<p>To fix this issue please set <b>{dep_app}</b> to version <b>{expected}</b>.</p>
	"""
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["incompatible-app-version"]

	# Traceback is not pertinent to issue
	details["traceback"] = None
	return True


def update_with_invalid_release_prebuild(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	if len(exc.args) != 4:
		return False

	_, app, hash, invalidation_reason = exc.args

	details["title"] = "Validation Failed: Invalid app release"
	message = f"""
	<p>App <b>{app}</b> has an invalid release with the commit hash
	<b>{hash[:10]}</b></p>

	<p>To rectify this, please fix the issue mentioned below and
	push a new update.</p>
	"""
	details["traceback"] = invalidation_reason
	details["message"] = fmt(message)
	return True


def update_with_required_app_not_found_prebuild(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	if len(exc.args) != 3:
		return False

	_, app, required_app = exc.args

	details["title"] = "Validation Failed: Required app not found"
	message = f"""
	<p><b>{app}</b> has a dependency on the app <b>{required_app}</b>
	which was not found on your bench.</p>

	<p>To rectify this issue, please add the required app to your Bench
	and try again.</p>
	"""
	details["traceback"] = None
	details["message"] = fmt(message)
	details["assistance_url"] = DOC_URLS["required-app-not-found"]
	return True


def update_with_vite_not_found(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	details["title"] = "Vite not found"
	failed_step = get_failed_step(dcb)
	if failed_step.stage_slug == "apps":
		app_name = failed_step.step
		message = f"""
		<p><b>{app_name}</b> installation has failed due the build
		dependency Vite not being found.</p>

		<p>To rectify this issue, please follow the steps mentioned
		in <i>Help</i>.</p>
		"""
	else:
		message = """
		<p>App installation has failed due the build dependency Vite
		not being found.</p>

		<p>To rectify this issue, please follow the steps mentioned
		in <i>Help</i>.</p>
		"""

	details["message"] = fmt(message)
	details["traceback"] = None
	details["assistance_url"] = DOC_URLS["vite-not-found"]
	return True


def update_with_yarn_install_failed(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	details["title"] = "App frontend dependency install failed"
	failed_step = get_failed_step(dcb)
	if failed_step.stage_slug == "apps":
		app_name = failed_step.step
		message = f"""
		<p><b>{app_name}</b> dependencies could not be installed.</p>

		<p>Please view the failing step <b>{failed_step.stage} - {failed_step.step}</b>
		output to debug and fix the error before retrying build.</p>

		<p>This may be due to issues with the app being installed
		and not Frappe Cloud.</p>
		"""

	else:
		message = """
		<p>App dependencies could not be installed.</p>

		<p>Please view the failing step output to debug and fix the error
		before retrying build.</p>

		<p>This may be due to issues with the app being installed
		and not Frappe Cloud.</p>
		"""

	details["message"] = fmt(message)
	details["traceback"] = None
	return True


def update_with_yarn_build_failed(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	details["title"] = "App frontend build failed"
	failed_step = get_failed_step(dcb)
	if failed_step.stage_slug == "apps":
		app_name = failed_step.step
		message = f"""
		<p><b>{app_name}</b> assets have failed to build.</p>

		<p>Please view the failing step <b>{failed_step.stage} - {failed_step.step}</b>
		output to debug and fix the error before retrying build.</p>

		<p>This may be due to issues with the app being installed
		and not Frappe Cloud.</p>
		"""

	else:
		message = """
		<p>App assets have failed to build.</p>

		<p>Please view the failing step output to debug and fix the error
		before retrying build.</p>

		<p>This may be due to issues with the app being installed
		and not Frappe Cloud.</p>
		"""

	details["message"] = fmt(message)
	details["traceback"] = None
	return True


def update_with_installation_file_not_found(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	details["title"] = "Missing or misconfigured package configuration file"

	failed_step = get_failed_step(dcb)
	if not failed_step or failed_step.stage_slug != "apps":
		return False

	message = f"""
                <p><b>{failed_step.step}</b> is missing a valid installation configuration file.</p>
				<p>Please add or correct a <code>pyproject.toml</code> (or <code>setup.cfg</code> / <code>setup.py</code>) with the required project metadata</p>
				<p>This issue is caused by the app's configuration and is not related to Frappe Cloud.</p>
            """

	details["message"] = fmt(message)
	details["traceback"] = None
	return True


def update_with_file_not_found(
	details: "Details",
	dc: "DeployCandidate",
	dcb: "DeployCandidateBuild",
	exc: BaseException,
):
	details["title"] = "File not found in app"

	if not (failed_step := get_failed_step(dcb)):
		return False

	if failed_step.stage_slug != "apps":
		return False

	app_name = failed_step.step

	# Non exact check for whether file not found originates in the
	# app being installed. If file not found is not in the app then
	# this is an unknown and not a user error.
	for line in dcb.build_output.split("\n"):
		if "FileNotFoundError: [Errno 2] No such file or directory" not in line:
			continue
		if app_name in line:
			break
		# In case of bad directory structure we can catch it using this since install always looks for init
		if (
			f"ERROR: [Errno 2] No such file or directory: './apps/{failed_step.step_slug}/{failed_step.step_slug}/__init__.py'"
			in line
		):
			break

	else:
		return False

	message = f"""
	<p><b>{app_name}</b> has a missing file.</p>

	<p>Please view the failing step <b>{failed_step.stage} - {failed_step.step}</b>
	output to find and add the missing file before retrying the build.</p>

	<p>This may be due to issues with the app being installed
	and not Frappe Cloud.</p>
	"""

	details["message"] = fmt(message)
	details["traceback"] = None
	return True


def check_if_app_updated(old_dcb: "DeployCandidateBuild", new_dc: "DeployCandidate") -> None:
	if not (failed_step := old_dcb.get_first_step("status", "Failure")):
		return

	if failed_step.stage_slug != "apps":
		return

	app_name = failed_step.step_slug
	old_app = get_dc_app(old_dcb.candidate, app_name)
	new_app = get_dc_app(new_dc, app_name)

	if new_app is None or old_app is None:
		return

	old_hash = old_app.hash or old_app.pullable_hash
	new_hash = new_app.hash or new_app.pullable_hash

	if old_hash != new_hash:
		return

	title = new_app.title or old_app.title
	frappe.throw(
		f"App <b>{title}</b> has not been updated since previous failing build. Release hash is <b>{new_hash[:10]}</b>.",
		BuildValidationError,
	)


def get_dc_app(dc: "DeployCandidate", app_name: str) -> "DeployCandidateApp | None":
	for app in dc.apps:
		if app.app == app_name:
			return app
	return None


def fmt(message: str) -> str:
	message = message.strip()
	message = dedent(message)
	return re.sub(r"\s+", " ", message)


def get_build_output_line(dc: "DeployCandidateBuild", needle: str):
	for line in dc.build_output.split("\n"):
		if needle in line:
			return line.strip()
	return ""


def get_app_from_incompatible_build_output_line(line: str):
	splits = line.split()
	if "error" not in splits:
		return ""

	idx = splits.index("error") + 1
	if len(splits) <= idx:
		return ""

	return splits[idx][:-1].split("@")[0]


def get_default_title(dc: "DeployCandidate") -> str:
	return "Build Failed"


def get_default_message(dcb: "DeployCandidateBuild") -> str:
	failed_step = dcb.get_first_step("status", "Failure")
	if failed_step:
		return f"Image build failed at step <b>{failed_step.stage} - {failed_step.step}</b>."
	return "Image build failed."


def get_is_actionable(dc: "DeployCandidate", tb: str) -> bool:
	return False


def get_ct_row(
	dcb: "DeployCandidateBuild",
	match_value: str,
	field: str,
	ct_field: str,
) -> Document | None:
	# This is fetching build step which is a part of build
	ct = dcb.get(field)
	if not ct:
		return None

	for row in ct:
		if row.get(ct_field) == match_value:
			return row

	return None


def get_failed_step(dcb: "DeployCandidateBuild"):
	return dcb.get_first_step("status", "Failure") or frappe._dict()
