# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.utils import system_manager_only


@press_mcp.tool()
@system_manager_only
def get_site_apps_info(site: str) -> dict:
	"""Repo and release info for all apps installed on a site.

	Returns bench, group, and per-app: source, release, hash, branch, repository_url.
	Use release name with get_app_release_clone_url to get a clone URL.
	"""
	if not frappe.db.exists("Site", site):
		frappe.throw(f"Site {site!r} not found")

	site_doc = frappe.get_doc("Site", site)
	bench_name = site_doc.bench

	if not bench_name:
		return {"site": site, "bench": None, "apps": [], "note": "site has no bench assigned"}

	installed_apps = {a.app for a in site_doc.apps}
	bench_apps = frappe.get_all(
		"Bench App",
		filters={"parent": bench_name},
		fields=["app", "source", "release", "hash"],
		order_by="idx asc",
	)

	return {
		"site": site,
		"bench": bench_name,
		"group": site_doc.group,
		"apps": [
			_app_metadata(ba.app, ba.source, ba.release, ba.hash)
			for ba in bench_apps
			if ba.app in installed_apps
		],
	}


@press_mcp.tool()
@system_manager_only
def get_bench_apps_info(bench: str) -> dict:
	"""Repo and release info for every app in a bench.

	Use release name with get_app_release_clone_url to get a clone URL.
	"""
	if not frappe.db.exists("Bench", bench):
		frappe.throw(f"Bench {bench!r} not found")

	bench_doc = frappe.get_doc("Bench", bench)

	return {
		"bench": bench,
		"group": bench_doc.group,
		"apps": [_app_metadata(ba.app, ba.source, ba.release, ba.hash) for ba in bench_doc.apps],
	}


@press_mcp.tool()
@system_manager_only
def get_app_release_clone_url(release: str) -> dict:
	"""Fresh clone URL for an App Release. Call immediately before cloning.

	Token in clone_url is valid for ~1 hour (GitHub limit).
	Never cache or reuse it — always call this tool right before running git.

	Clone steps:
		DIR = local_dir  # from this response

		if [ -d "$DIR" ]; then
			echo "already cloned, skipping"
		else
			mkdir -p "$DIR" && cd "$DIR"
			git init
			git remote add origin <clone_url>
			git fetch --depth 1 origin <hash>
			git checkout <hash>
			git reset --hard <hash>
			git remote set-url origin <repository_url>
		fi

	If git fetch fails (token expired): call this tool again with the same
	arguments and retry with the new clone_url.

	After cloning: discard clone_url, use repository_url for display.
	"""
	release_doc = frappe.db.get_value(
		"App Release",
		release,
		["app", "source", "hash"],
		as_dict=True,
	)
	if not release_doc:
		frappe.throw(f"App Release {release!r} not found")

	return _app_clone_info(release_doc.app, release_doc.source, release, release_doc.hash)


def _app_metadata(
	app: str,
	source_name: str,
	release_name: str | None,
	commit_hash: str | None,
) -> dict:
	source = frappe.get_doc("App Source", source_name)
	return {
		"app": app,
		"source": source_name,
		"release": release_name,
		"repository_url": source.repository_url,
		"repository_owner": source.repository_owner,
		"repository": source.repository,
		"branch": source.branch,
		"hash": commit_hash,
	}


def _app_clone_info(
	app: str,
	source_name: str,
	release_name: str,
	commit_hash: str,
) -> dict:
	source = frappe.get_doc("App Source", source_name)
	is_private = bool(source.github_installation_id)

	clone_url = None
	error = None

	try:
		clone_url = source.get_repo_url()
	except Exception as e:
		error = str(e)

	result: dict = {
		"app": app,
		"source": source_name,
		"release": release_name,
		"repository_url": source.repository_url,
		"repository_owner": source.repository_owner,
		"repository": source.repository,
		"branch": source.branch,
		"hash": commit_hash,
		"private": is_private,
		"clone_url": clone_url,
		"clone_url_expires_in_minutes": 60 if is_private else None,
		"sensitive_fields": ["clone_url"],
		"local_dir": "cloned_repos/{}_{}".format(app.replace("/", "_"), release_name.replace("/", "_")),
	}

	if error:
		result["error"] = error

	return result
