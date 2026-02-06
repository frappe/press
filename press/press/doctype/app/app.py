# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import typing

import frappe
import rq
import semantic_version as sv
from frappe.model.document import Document

from press.utils.jobs import has_job_timeout_exceeded

if typing.TYPE_CHECKING:
	from press.press.doctype.app_source.app_source import AppSource


class App(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		branch: DF.Data | None
		enable_auto_deploy: DF.Check
		enabled: DF.Check
		frappe: DF.Check
		installation: DF.Data | None
		public: DF.Check
		repo: DF.Data | None
		repo_owner: DF.Data | None
		scrubbed: DF.Data | None
		skip_review: DF.Check
		team: DF.Link | None
		title: DF.Data
		url: DF.Data | None
	# end: auto-generated types

	dashboard_fields = ("title",)

	def add_source(
		self,
		repository_url,
		branch,
		frappe_version: str,
		team=None,
		github_installation_id=None,
		public=False,
		repository_owner=None,
	) -> "AppSource":
		# Ensure no .git suffix when looking for existing sources
		supported_frappe_versions = parse_frappe_version(frappe_version)
		repository_url = repository_url.removesuffix(".git")
		existing_source = frappe.get_all(
			"App Source",
			{"app": self.name, "repository_url": repository_url, "branch": branch, "team": team},
			limit=1,
		)
		if existing_source:
			source = frappe.get_doc("App Source", existing_source[0].name)
			versions = set(version.version for version in source.versions)
			new_versions = supported_frappe_versions - versions
			for new_version in new_versions:
				source.add_version(new_version)
		else:
			# Add new App Source
			source = frappe.get_doc(
				{
					"doctype": "App Source",
					"app": self.name,
					"versions": [{"version": v} for v in supported_frappe_versions],
					"repository_url": repository_url,
					"branch": branch,
					"team": team,
					"github_installation_id": github_installation_id,
					"public": public,
					"repository_owner": repository_owner,
				}
			).insert()
		return source

	def before_save(self):
		self.frappe = self.name == "frappe"


def new_app(name, title):
	app: "App" = frappe.get_doc({"doctype": "App", "name": name, "title": title}).insert()
	return app


def poll_new_releases():
	for source in frappe.get_all(
		"App Source",
		{"enabled": True, "last_github_poll_failed": False},
		order_by="last_synced asc",
		limit=300,
	):
		if has_job_timeout_exceeded():
			return
		try:
			source = frappe.get_doc("App Source", source.name)
			source.create_release()
			frappe.db.commit()
		except rq.timeouts.JobTimeoutException:
			frappe.db.rollback()
			return
		except Exception:
			frappe.db.rollback()


def is_bounded(spec: sv.NpmSpec) -> bool:
	# NpmSpec.clause_groups is a list of requirement sets (OR logic)
	standardized = str(spec)

	if "*" in standardized or not standardized:
		return False

	# A bounded range must have a 'less than' component
	# OR be a specific version (==)
	has_upper_bound = "<" in standardized
	has_lower_bound = ">" in standardized

	if "==" in standardized or (">" not in standardized and "<" not in standardized):
		return True

	return has_upper_bound and has_lower_bound


def map_frappe_version(version_string: str, frappe_versions: list[dict[str, int | str]]) -> list[str]:
	"""Map a version spec to supported Frappe versions."""
	matched = []
	try:
		version_string = version_string.replace(" ", "").replace(",", " ")
		spec = sv.NpmSpec(version_string)
	except ValueError:
		frappe.throw("Invalid version format. Please use NPM-style semver ranges (e.g. '>=15.0.0 <16.0.0').")

	if not is_bounded(spec):
		frappe.throw("Please provide a bounded version range (e.g. '>=15.0.0 <16.0.0').")

	highest_supported_stable_version = sv.Version(
		f"{max(version['number'] for version in frappe_versions if version['status'] == 'Stable')}.0.0",
	)

	for version in frappe_versions:
		supported_version = sv.Version(
			f"{version['number']}.0.0"
		)  # Converting frappe version number (16 -> 16.0.0)
		if spec.match(supported_version):
			matched.append(str(version["name"]))

	# Check if the spec can support more than the highest stable version
	if spec.match(highest_supported_stable_version.next_patch()):
		matched.append("Nightly")

	return matched


def parse_frappe_version(version_string: str) -> set[str]:
	"""Parse the Frappe version from a version string."""
	frappe_versions = frappe.get_all(
		"Frappe Version",
		{"public": True},
		["name", "number", "status"],
	)
	# This is already supported return quick
	if version_string in [frappe_version["name"] for frappe_version in frappe_versions]:
		return set([version_string] if isinstance(version_string, str) else version_string)

	if frappe.flags.in_test and version_string in [
		"Version 12",
		"Version 13",
		"Version 14",
		"Version 15",
		"Version 16",
		"Nightly",
	]:
		return set([version_string] if isinstance(version_string, str) else version_string)

	return set(map_frappe_version(version_string, frappe_versions))
