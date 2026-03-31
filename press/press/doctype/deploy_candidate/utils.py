from __future__ import annotations

import json
import re
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

import frappe

if TYPE_CHECKING:
	from press.press.doctype.release_group.release_group import ReleaseGroup


class BuildWarning(Warning):
	pass


class PackageManagers(TypedDict):
	repo_path: str
	pyproject: dict[str, Any] | None
	packagejsons: list[dict[str, Any]]


PackageManagerFiles = dict[str, PackageManagers]


def get_package_manager_files(repo_path_map: dict[str, str]) -> PackageManagerFiles:
	# Return pyproject.toml and package.json files
	pfiles_map = {}
	for app, repo_path in repo_path_map.items():
		pfiles_map[app] = get_package_manager_files_from_repo(app, repo_path)

	return pfiles_map


def get_package_manager_files_from_repo(app: str, repo_path: str):
	pypt, pckjs = _get_package_manager_files_from_repo(
		repo_path,
		True,
	)

	pm: PackageManagers = {
		"repo_path": repo_path,
		"pyproject": None,
		"packagejsons": [],
	}

	if pypt is not None:
		pm["pyproject"] = load_pyproject(app, pypt.absolute().as_posix())

	for pckj in pckjs:
		package_json = load_package_json(
			app,
			pckj.absolute().as_posix(),
		)
		pm["packagejsons"].append(package_json)

	return pm


def _get_package_manager_files_from_repo(
	repo_path: str,
	recursive: bool,
) -> tuple[Path | None, list[Path]]:
	pyproject_toml: Path | None = None
	package_jsons: list[Path] = []  # An app can have multiple

	for p in Path(repo_path).iterdir():
		if p.name == "pyproject.toml":
			pyproject_toml = p
		elif p.name == "package.json":
			package_jsons.append(p)

		if not (recursive and p.is_dir()):
			continue

		pypt, pckjs = _get_package_manager_files_from_repo(p, False)
		if pypt is not None and pyproject_toml is None:
			pyproject_toml = pypt

		package_jsons.extend(pckjs)

	return pyproject_toml, package_jsons


def load_pyproject(app: str, pyproject_path: str):
	try:
		from tomli import TOMLDecodeError, load
	except ImportError:
		from tomllib import TOMLDecodeError, load  # type: ignore

	with open(pyproject_path, "rb") as f:
		try:
			return load(f)
		except TOMLDecodeError:
			# Do not edit without updating deploy_notifications.py
			raise Exception("App has invalid pyproject.toml file", app) from None


def load_package_json(app: str, package_json_path: str):
	with open(package_json_path, "rb") as f:
		try:
			return json.load(f)
		except json.JSONDecodeError:
			# Do not edit without updating deploy_notifications.py
			raise Exception("App has invalid package.json file", app, package_json_path) from None


def get_error_key(error_substring: str | list[str]) -> str:
	if isinstance(error_substring, list):
		error_substring = " ".join(error_substring)
	"""
	Converts `MatchStrings` into error keys, these are set on
	DeployCandidates on UA Failures for two reasons:
	1. To check if a subsequent deploy will fail for the same reasons.
	2. To track the kind of UA errors the users are facing.
	"""

	return re.sub(
		r"[\"'\[\],:]|\.$",
		"",
		error_substring.lower(),
	)


def get_will_fail_checker(error_key: str):
	from press.press.doctype.deploy_candidate.deploy_notifications import handlers

	for error_substring, _, will_fail_checker in handlers():
		if get_error_key(error_substring) == error_key:
			return will_fail_checker

	return None


def is_suspended() -> bool:
	return bool(frappe.db.get_single_value("Press Settings", "suspend_builds"))


class BuildValidationError(frappe.ValidationError): ...


def get_build_server(group: str | None = None) -> str | None:
	"""
	Order of build server selection precedence:
	1. Build Server set on Release Group
	2. Build Server with least active builds
	3. Build Server set in Press Settings
	This returns the build server based on the first server in the release group
	depending on the platform of the server, if more servers exist in the release group
	deploy candidate will trigger another build based on the platform of the next server
	from either of the following functions
		- get_intel_build_server_with_least_active_builds
		- get_arm_build_server_with_least_active_builds
	"""

	if group and (server := frappe.get_value("Release Group", group, "build_server")):
		return server

	if group:
		release_group: ReleaseGroup = frappe.get_doc("Release Group", group)
		for server in release_group.servers:
			server_platform = frappe.get_value("Server", server.server, "platform")
			if server_platform == "arm64":
				if server := get_arm_build_server_with_least_active_builds():
					return server
			else:
				if server := get_intel_build_server_with_least_active_builds():
					return server
	else:
		if server := get_intel_build_server_with_least_active_builds():
			return server

	return frappe.get_value("Press Settings", None, "build_server")


def get_intel_build_server_with_least_active_builds() -> str | None:
	return get_build_server_with_least_active_builds(platform="x86_64")


def get_arm_build_server_with_least_active_builds() -> str | None:
	return get_build_server_with_least_active_builds(platform="arm64")


def get_build_server_with_least_active_builds(platform: str) -> str | None:
	build_servers = frappe.get_all(
		"Server",
		filters={"use_for_build": True, "status": "Active", "platform": platform},
		pluck="name",
	)

	if not build_servers:
		return None

	if len(build_servers) == 1:
		return build_servers[0]

	build_count = get_active_build_count_by_build_server()

	# Build server might not be in build_count, or might be inactive
	build_count_tuples = [(s, build_count.get(s, 0)) for s in build_servers]
	build_count_tuples.sort(key=lambda x: x[1])
	return build_count_tuples[0][0]


def get_active_build_count_by_build_server():
	build_servers = frappe.get_all(
		"Deploy Candidate Build",
		fields=["build_server"],
		filters={
			"status": ["in", ["Running", "Preparing"]],
			"modified": [">", frappe.utils.now_datetime() - timedelta(hours=4)],
		},
		pluck="build_server",
	)
	return Counter(build_servers)
