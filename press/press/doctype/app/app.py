# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import typing

import frappe
import rq
import semantic_version as sv
from frappe.model.document import Document

from press.utils.jobs import has_job_timeout_exceeded

if typing.TYPE_CHECKING:
	from collections.abc import Iterator

	from semantic_version.base import AllOf, AnyOf

	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.app_source.app_source import AppSource


class VersioningError(Exception): ...


class AppPolicyResult(typing.TypedDict):
	app: str
	source: str


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
		supported_frappe_versions = parse_frappe_version(frappe_version, self.title)
		repository_url = repository_url.removesuffix(".git")
		existing_source = frappe.get_all(
			"App Source",
			{"app": self.name, "repository_url": repository_url, "branch": branch, "team": team},
			limit=1,
		)
		if existing_source:
			source: AppSource = frappe.get_doc("App Source", existing_source[0].name)
			versions = set(version.version for version in source.versions)
			new_versions = supported_frappe_versions - versions
			# The hacks below are to ensure that we don't call save on the `App Source` document
			# Triggering validations and other logic might fail app addition
			# This is temporary until we merge all app sources!
			for idx, new_version in enumerate(new_versions, start=0):
				frappe.get_doc(
					{
						"doctype": "App Source Version",
						"parenttype": "App Source",
						"parentfield": "versions",
						"parent": source.name,
						"version": new_version,
						"idx": len(source.versions) + idx + 1,
					}
				).insert()

			if github_installation_id and source.github_installation_id != github_installation_id:
				frappe.db.set_value(
					"App Source", source.name, "github_installation_id", github_installation_id
				)
		else:
			# Add new App Source
			if not supported_frappe_versions:
				frappe.throw(
					f"{frappe_version} does not match any supported versions, try relaxing the version constrains",
					VersioningError,
				)

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
	"""Ensure less than and greater than bounds are there, or exact version is given"""
	standardized = str(spec)

	if "*" in standardized or not standardized:
		return False

	has_upper_bound = "<" in standardized
	has_lower_bound = ">" in standardized

	return has_upper_bound and has_lower_bound


def _iter_clause_tree(spec: sv.NpmSpec | AllOf | AnyOf) -> Iterator:
	if hasattr(spec, "operator"):
		yield spec

	elif hasattr(spec, "clause"):
		yield from _iter_clause_tree(spec.clause)

	elif hasattr(spec, "clauses"):
		for clause in spec.clauses:
			yield from _iter_clause_tree(clause)


def get_lower_bound_major(spec: sv.NpmSpec) -> int | None:
	"""Fetch lower bound major version from the spec take into account multiple lower bounds"""
	lowers = [
		c.target
		for c in _iter_clause_tree(spec)
		if getattr(c, "operator", None) in (">", ">=") and getattr(c, "target", None) is not None
	]
	uppers = [
		c.target
		for c in _iter_clause_tree(spec)
		if getattr(c, "operator", None) in ("<", "<=") and getattr(c, "target", None) is not None
	]

	# Ensure that there is no overlap or inconsistency between upper and lower bounds
	if any(upper.major < lower.major for upper in uppers for lower in lowers):
		frappe.throw(
			"Invalid version range: There is an inconsistency between the upper and lower bound major versions. "
			"Please ensure the version range specifies valid major versions."
		)

	return min(lowers).major


def map_frappe_version(
	version_string: str,
	frappe_versions: list[dict[str, int | str]],
	app_title: str,
	ease_versioning_constrains: bool = False,
) -> list[str]:
	"""Map a version spec to supported Frappe versions."""
	matched = []
	try:
		version_string = version_string.replace(" ", "").replace(",", " ")
		spec = sv.NpmSpec(version_string)
	except ValueError:
		frappe.throw(
			f"Invalid version format for app '{app_title}'. Please use NPM-style semver ranges (e.g. '>=15.0.0 <16.0.0')."
		)

	if not is_bounded(spec):
		frappe.throw(
			f"Version range must be bounded for app '{app_title}'. "
			"Please provide both a lower and an upper bound "
			"(e.g. '>=15.0.0 <16.0.0')."
		)

	highest_supported_stable_version = sv.Version(
		f"{max(version['number'] for version in frappe_versions if version['status'] == 'Stable')}.0.0",
	)

	for version in frappe_versions:
		supported_version = sv.Version(
			f"{version['number']}.0.0"
		)  # Converting frappe version number (16 -> 16.0.0)
		if spec.match(supported_version):
			matched.append(str(version["name"]))

		if ease_versioning_constrains:
			# Get major version of the lower bound
			lower_bound_major = get_lower_bound_major(spec)
			if lower_bound_major == version["number"] and str(version["name"]) not in matched:
				matched.append(str(version["name"]))

	# Check if the spec can support more than the highest stable version
	if (
		spec.match(highest_supported_stable_version.next_patch())
		or spec.match(highest_supported_stable_version.next_minor())
		or spec.match(highest_supported_stable_version.next_major())
	):
		matched.append("Nightly")

	return matched


def parse_frappe_version(
	version_string: str, app_title: str, ease_versioning_constrains: bool = False
) -> set[str]:
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

	return set(map_frappe_version(version_string, frappe_versions, app_title, ease_versioning_constrains))


def get_app_source_from_supported_versions(app: str, supported_versions: set[str]) -> AppSource | None:
	"""From the provided versions fetch the app source which supports the latest version.
	In case no app supports the latest version the just get whatever app source supports any of the provided versions.
	"""
	version_numbers = frappe.get_all(
		"Frappe Version", {"name": ("in", supported_versions)}, ["name", "number"]
	)
	version_numbers = sorted(version_numbers, key=lambda x: x["number"], reverse=True)

	app_source = frappe.qb.DocType("App Source")
	app_source_version = frappe.qb.DocType("App Source Version")

	base_query = (
		frappe.qb.from_(app_source)
		.join(app_source_version)
		.on(app_source.name == app_source_version.parent)
		.where(app_source.app == app)
		.select(app_source.name)
		.groupby(app_source.name)
		.limit(1)
	)

	highest_priority_query = base_query.where(app_source_version.version == version_numbers[0]["name"])
	highest_priority_app_source = highest_priority_query.run(pluck=True)

	if highest_priority_app_source:
		return frappe.get_doc("App Source", highest_priority_app_source[0])

	any_matching_app_source = base_query.where(app_source_version.version.isin(supported_versions))
	any_matching_app_source = any_matching_app_source.run(pluck=True)
	return frappe.get_doc("App Source", any_matching_app_source[0]) if any_matching_app_source else None


def get_latest_release_of_app_from_source(app_source: AppSource) -> AppRelease | None:
	app_release_info = frappe.db.get_value(
		"App Release",
		{"app": app_source.app, "source": app_source.name},
		["name", "hash"],
		order_by="creation",
	)

	if not app_release_info:
		return None

	return frappe.get_doc("App Release", app_release_info[0])


def get_app_from_policies(
	version: str, for_creation: bool = False, for_installation: bool = False
) -> list[AppPolicyResult]:
	"""Get all apps based on the policy results for a given version string"""
	ReleaseGroupPolicy = frappe.qb.DocType("Release Group Policy")
	ReleaseGroupPolicyApp = frappe.qb.DocType("Release Group Policy App")

	policy_result = (
		frappe.qb.from_(ReleaseGroupPolicy)
		.join(ReleaseGroupPolicyApp)
		.on(ReleaseGroupPolicyApp.parent == ReleaseGroupPolicy.name)
		.where(ReleaseGroupPolicy.version == version)
		.where(ReleaseGroupPolicy.status == "Active")
		.select(ReleaseGroupPolicyApp.app, ReleaseGroupPolicyApp.source)
	)

	if for_creation:
		policy_result = policy_result.where(
			ReleaseGroupPolicyApp.add_on_creation == 1,
		)

	if for_installation:
		policy_result = policy_result.where(
			ReleaseGroupPolicyApp.install_on_site_creation == 1,
		)

	return policy_result.run(as_dict=True)
