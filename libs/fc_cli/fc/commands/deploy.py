from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from fc.printer import Print

if TYPE_CHECKING:
	from fc.authentication.session import CloudSession


deploy = typer.Typer(help="Bench/Deploy Commands")
console = Console()


# Trigger initial deploy for a bench group
@deploy.command(help="Trigger initial deploy for a bench group")
def bench_init(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Bench group name")],
	force: Annotated[
		bool,
		typer.Option("--force", "-f", is_flag=True, help="Skip confirmation"),
	] = False,
):
	session: CloudSession = ctx.obj
	payload = {
		"dt": "Release Group",
		"dn": name,
		"method": "initial_deploy",
		"args": None,
	}
	try:
		if not _should_proceed(
			f"Trigger initial deploy for bench group '{name}'? This will start a full build & deploy.",
			force,
		):
			Print.info(console, "Operation cancelled.")
			return
		url = _build_method_url(session, "press.api.client.run_doc_method")
		response = session.post(
			url, json=payload, message=f"[bold green]Triggering initial deploy for '{name}'..."
		)
		if response and (response.get("success") or not response.get("exc_type")):
			Print.success(console, f"Initial deploy triggered for bench group:{name}")
		else:
			error_msg = response.get("message") or response.get("exception") or "Unknown error"
			Print.error(console, f"Failed to trigger initial deploy: {error_msg}")
	except Exception as e:
		Print.error(console, f"Error triggering initial deploy: {e}")


@deploy.command(help="Create bench group")
def create_bench_group(
	ctx: typer.Context,
	version: Annotated[str, typer.Argument(help="Frappe Framework Version (e.g. Version 15)")],
	region: Annotated[str, typer.Argument(help="Region (cluster name, e.g. Mumbai)")],
	title: Annotated[str, typer.Argument(help="Bench Group Title (e.g. cli-test-bench)")],
	server: Annotated[str, typer.Argument(help="Server name")],
):
	session: CloudSession = ctx.obj
	try:
		options_url = _bench_options_url(session)
		options = session.get(options_url)
		frappe_source = _find_frappe_source(options, version)
		if not frappe_source:
			Print.error(console, f"Could not find valid source for frappe in version '{version}'.")
			return
		_warn_server_name_format(server)
		_create_bench(session, title, version, region, frappe_source, server)
	except Exception as e:
		Print.error(console, f"Error creating bench group: {e}")


@deploy.command(help="Drop (archive) a bench group")
def drop_bench_group(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Bench group name to drop/archive")],
	force: Annotated[
		bool,
		typer.Option("--force", "-f", is_flag=True, help="Skip confirmation"),
	] = False,
):
	session: CloudSession = ctx.obj
	try:
		if not _should_proceed(
			f"Are you sure you want to drop/archive bench group '{name}'? This action may be irreversible.",
			force,
		):
			Print.info(console, "Operation cancelled.")
			return

		payload = {"doctype": "Release Group", "name": name}
		delete_url = _build_method_url(session, "press.api.client.delete")
		response = session.post(
			delete_url,
			json=payload,
			message=f"[bold red]Dropping bench group '{name}'...",
		)
		if response and response.get("exc_type"):
			Print.error(console, f"Failed to drop bench group: {response.get('exception', 'Unknown error')}")
			return
		# Consider success if no error and either 'success' is True or no error but response is present
		if response.get("success") or (response and not response.get("exc_type")):
			Print.success(console, f"Successfully dropped bench group: {name}")
		else:
			error_msg = response.get("message") or response.get("exception") or "Unknown error"
			Print.error(console, f"Failed to drop bench group: {error_msg}")
	except Exception as e:
		Print.error(console, f"Error dropping bench group: {e}")


@deploy.command(help="Add app to bench group by name and version")
def add_app(
	ctx: typer.Context,
	bench: Annotated[str, typer.Argument(help="Bench group name")],
	app: Annotated[str, typer.Argument(help="App name")],
	branch: Annotated[str, typer.Argument(help="App branch (e.g. 'version-15-beta')")],
):
	session: CloudSession = ctx.obj
	url = _build_method_url(session, "press.api.bench.all_apps")
	payload = {"name": bench}
	try:
		response = session.post(url, json=payload)
		if not response or not isinstance(response, list):
			Print.error(console, "Failed to fetch apps list.")
			return
		source = _find_app_source(response, app, branch)
		if not source:
			Print.error(console, f"Source not found for app '{app}' and branch '{branch}'")
			return
		add_url = _build_method_url(session, "press.api.bench.add_app")
		add_payload = {"name": bench, "source": source, "app": app}
		add_response = session.post(add_url, json=add_payload)
		if isinstance(add_response, dict):
			if add_response.get("success") or not add_response.get("exc_type"):
				Print.success(
					console, f"Successfully added app '{app}' (branch '{branch}') to bench '{bench}'"
				)
			else:
				error_msg = (
					add_response.get("message")
					or add_response.get("exception")
					or add_response.get("exc")
					or "Unknown error"
				)
				Print.error(console, f"Failed to add app '{app}' to bench '{bench}': {error_msg}")
		elif isinstance(add_response, str):
			# Handle string response (e.g. when app is already added or not found)
			if "already exists" in add_response:
				Print.info(console, f"App '{app}' is already added to bench '{bench}'.")
			else:
				Print.error(console, f"Failed to add app '{app}' to bench '{bench}': {add_response}")
		else:
			Print.error(console, f"Failed to add app '{app}' to bench '{bench}': Unknown error")
	except Exception as e:
		Print.error(console, f"Error adding app: {e}")


@deploy.command(help="Remove app from bench group")
def remove_app(
	ctx: typer.Context,
	bench: Annotated[str, typer.Argument(help="Bench group name")],
	app: Annotated[str, typer.Argument(help="App name to remove")],
):
	session: CloudSession = ctx.obj
	url = _build_method_url(session, "press.api.client.run_doc_method")
	payload = {"dt": "Release Group", "dn": bench, "method": "remove_app", "args": {"app": app}}
	try:
		response = session.post(url, json=payload)
		if isinstance(response, dict):
			if response.get("success") or not response.get("exc_type"):
				Print.success(console, f"Successfully removed app '{app}' from bench '{bench}'")
			else:
				error_msg = (
					response.get("message")
					or response.get("exception")
					or response.get("exc")
					or "Unknown error"
				)
				Print.error(console, f"Failed to remove app '{app}' from bench '{bench}': {error_msg}")
		elif isinstance(response, str):
			# If response is just the app name, treat as success (already removed or not present)
			if response.strip() == app:
				Print.success(console, f"Successfully removed app '{app}' from bench '{bench}'")
			elif "not found" in response or "does not exist" in response:
				Print.info(console, f"App '{app}' is not present in bench '{bench}'.")
			else:
				Print.error(console, f"Failed to remove app '{app}' from bench '{bench}': {response}")
		else:
			Print.error(console, f"Failed to remove app '{app}' from bench '{bench}': Unknown error")
	except Exception as e:
		Print.error(console, f"Error removing app: {e}")


if __name__ == "__main__":
	pass


@deploy.command(help="Update a single app in a bench by release hash prefix")
def update_app(
	ctx: typer.Context,
	app: Annotated[str, typer.Argument(help="App name to update (e.g. india_compliance)")],
	hash_prefix: Annotated[
		str, typer.Argument(help="First few characters of the target release git hash (min 5)")
	],
	bench: Annotated[
		str | None,
		typer.Argument(help="Bench group name (optional; auto-detect by app)"),
	] = None,
):
	"""Find the app release whose commit hash starts with HASH_PREFIX and trigger deploy_and_update.

	Workflow:
	- Fetch deploy information for the bench (apps and their upcoming releases)
	- Find the app entry and match release by git hash prefix
	- Call press.api.bench.deploy_and_update with the selected release
	"""
	session: CloudSession = ctx.obj

	try:
		# Auto-detect bench if not provided
		target_bench = bench or _auto_detect_bench_for_app(session, app)
		if not target_bench:
			Print.error(
				console,
				"Could not determine bench group. Please pass bench explicitly or ensure the app is present in a bench.",
			)
			return

		_warn_if_short_hash(hash_prefix)

		# Get deploy information (includes upcoming releases per app)
		info = (
			session.get(
				"press.api.bench.deploy_information",
				params={"name": target_bench},
			)
			or {}
		)

		app_entry = _pick_app_entry(info, app)
		if not app_entry:
			Print.error(console, f"App '{app}' not found in bench '{target_bench}'.")
			return

		selected_release, selected_hash = _select_release_by_prefix(
			app_entry.get("releases", []) or [], hash_prefix
		)
		if not selected_release:
			# _select_release_by_prefix already printed helpful messages
			return

		payload = {
			"name": target_bench,
			"apps": [{"app": app, "release": selected_release}],
			"sites": [],
			"run_will_fail_check": False,
		}

		result = session.post(
			"press.api.bench.deploy_and_update",
			json=payload,
			message=(
				f"[bold green]Updating app '{app}' on bench '{target_bench}' to release {selected_release}"
				f" (hash {selected_hash[:12]})..."
			),
		)

		if _is_success_response(result):
			# Response is typically a deploy candidate/build name (string) or success dict.
			if isinstance(result, str) and result:
				Print.success(console, f"Update scheduled. Tracking name: {result}")
			else:
				Print.success(console, "Update scheduled successfully.")
		else:
			Print.error(console, f"Failed to schedule update: {_format_error_message(result)}")

		# No separate deploy call needed; deploy_and_update already schedules build + deploy.

	except Exception as e:
		Print.error(console, f"Error scheduling app update: {e}")


def _pick_app_entry(info: dict, app: str) -> dict | None:
	apps = info.get("apps", []) or []
	return next((a for a in apps if (a.get("app") == app or a.get("name") == app)), None)


def _select_release_by_prefix(releases: list[dict], hash_prefix: str) -> tuple[str | None, str]:
	"""Return (release_name, hash) matching the given hash prefix, else (None, "").

	Prints concise error messages on ambiguity or no-match.
	"""
	matches = [r for r in releases if str(r.get("hash", "")).startswith(hash_prefix)]
	if not matches:
		suggestions = ", ".join([r.get("hash", "")[:7] for r in releases][:10])
		if suggestions:
			Print.error(console, f"No matching release found. Try one of: {suggestions} ...")
		else:
			Print.error(console, "No releases available to match against.")
		return None, ""

	if len(matches) > 1:
		details = ", ".join([f"{r.get('hash', '')[:12]} ({r.get('name')})" for r in matches])
		Print.error(console, f"Ambiguous hash prefix; matches multiple releases: {details}")
		return None, ""

	selected = matches[0]
	return selected.get("name"), selected.get("hash", "")


def _warn_if_short_hash(hash_prefix: str) -> None:
	if len(hash_prefix) < 5:
		Print.warn(console, "Hash prefix is very short; using at least 5 characters reduces ambiguity.")


def _is_success_response(result: object) -> bool:
	if isinstance(result, str):
		return bool(result)
	if isinstance(result, dict):
		return bool(result.get("success") or not result.get("exc_type"))
	return False


def _format_error_message(result: object) -> str:
	if isinstance(result, dict):
		return str(result.get("message") or result.get("exception") or result) or "Unknown error"
	return str(result) or "Unknown error"


def _should_proceed(message: str, confirm_token: str | None) -> bool:
	if isinstance(confirm_token, bool) and confirm_token:
		return True
	if isinstance(confirm_token, str) and confirm_token.lower() in {"force", "yes", "y"}:
		return True
	return typer.confirm(message, default=False)


# --------------------
# Helper functions (grouped at bottom for structure)
# --------------------


def _build_method_url(session: "CloudSession", method: str) -> str:
	"""Build a full URL to an API method using the session's base URL."""
	base_url = session.base_url.rstrip("/")
	if base_url.endswith("/api/method"):
		base_url = base_url[: -len("/api/method")]
	return f"{base_url}/api/method/{method}"


def _bench_options_url(session: "CloudSession") -> str:
	"""Build bench options URL from session.base_url consistently."""
	return _build_method_url(session, "press.api.bench.options")


def _prepare_bench_payload(
	title: str,
	version: str,
	region: str,
	frappe_source: str,
	server: str,
) -> dict:
	return {
		"title": title,
		"version": version,
		"cluster": region,
		"apps": [{"name": "frappe", "source": frappe_source}],
		"saas_app": "",
		"server": server.strip().rstrip("\\"),
	}


def _auto_detect_bench_for_app(session: "CloudSession", app: str) -> str | None:
	"""Return the first bench name that contains the given app, else None."""
	benches_url = _build_method_url(session, "press.api.bench.all")
	benches = session.get(benches_url) or []
	for bench in benches:
		for app_entry in bench.get("apps", []) or []:
			if app_entry.get("app") == app:
				return bench.get("name")
	return None


def _get_source_and_release(
	session: "CloudSession", bench_name: str, app: str, branch: str | None
) -> tuple[str | None, str | None]:
	"""Resolve (source, release) for app on a bench, optionally filtering by branch."""
	apps_url = _build_method_url(session, "press.api.bench.all_apps")
	apps_response = session.post(apps_url, json={"name": bench_name})
	if not isinstance(apps_response, list):
		return None, None
	for entry in apps_response:
		if entry.get("app") != app:
			continue
		for src in entry.get("sources", []) or []:
			if branch and src.get("branch") != branch:
				continue
			return src.get("name"), src.get("release")
	return None, None


def _find_frappe_source(options: dict, version: str) -> str | None:
	"""Given bench options and a version, return the frappe source name or None."""
	try:
		for v in options.get("versions", []):
			if v.get("name") == version:
				for a in v.get("apps", []):
					if a.get("name") == "frappe":
						src = a.get("source", {})
						return src.get("name")
	except Exception:
		return None
	return None


def _find_app_source(apps_list: list[dict], app: str, branch: str) -> str | None:
	"""Find source name for an app/branch in the all_apps response."""
	for entry in apps_list:
		if entry.get("app") == app:
			for src in entry.get("sources", []):
				if src.get("branch") == branch:
					return src.get("name")
	return None


def _warn_server_name_format(server: str) -> None:
	if server.endswith("\\") or server.strip() != server:
		Print.warn(console, "Server name contains trailing backslash or spaces. Please check your input.")


def _create_bench(
	session: "CloudSession",
	title: str,
	version: str,
	region: str,
	frappe_source: str,
	server: str,
) -> None:
	bench_payload = _prepare_bench_payload(title, version, region, frappe_source, server)
	try:
		response = session.post(
			"press.api.bench.new",
			json={"bench": bench_payload},
			message=f"[bold green]Creating bench group '{title}' for version '{version}', region '{region}', and server '{server}'...",
		)
		if isinstance(response, dict) and response.get("success"):
			Print.success(console, f"Successfully created bench group: {title}")
		elif isinstance(response, dict):
			# Show only the main error message if present
			msg = (
				response.get("message") or response.get("exception") or response.get("exc") or "Unknown error"
			)
			Print.error(console, f"Failed to create bench group: {msg}")
		elif isinstance(response, str):
			Print.success(console, f"Successfully created bench group: {response}")
		else:
			Print.error(console, f"Backend error: {response}")
	except Exception as req_exc:
		# Show only the exception message
		Print.error(console, f"Request error: {req_exc}")
