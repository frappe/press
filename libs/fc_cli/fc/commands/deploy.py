from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer

from fc.commands.utils import handle_exception, print_error, print_info, print_success

if TYPE_CHECKING:
	from fc.authentication.session import CloudSession


deploy = typer.Typer(help="Bench/Deploy Commands")


# Trigger initial deploy for a bench group
@deploy.command(help="Trigger initial deploy for a bench group")
def bench_init(
	ctx: typer.Context,
	name: Annotated[str, typer.Option("--name", help="Bench group name")] = ...,
):
	session: CloudSession = ctx.obj
	payload = {
		"dt": "Release Group",
		"dn": name,
		"method": "initial_deploy",
		"args": None,
	}
	try:
		url = _build_method_url(session, "press.api.client.run_doc_method")
		response = session.post(
			url, json=payload, message=f"[bold green]Triggering initial deploy for '{name}'..."
		)
		if response and (response.get("success") or not response.get("exc_type")):
			print_success(f"Initial deploy triggered for bench group:{name}")
		else:
			error_msg = response.get("message") or response.get("exception") or "Unknown error"
			print_error(f"Failed to trigger initial deploy: {error_msg}")
	except Exception as e:
		handle_exception(e, "Error triggering initial deploy")


@deploy.command(help="Create bench group")
def create_bench_group(
	ctx: typer.Context,
	version: Annotated[
		str, typer.Option("--version", help="Frappe Framework Version (e.g. Version 15)")
	] = ...,
	region: Annotated[str, typer.Option("--region", help="Region (cluster name, e.g. Mumbai)")] = ...,
	title: Annotated[str, typer.Option("--title", help="Bench Group Title (e.g. cli-test-bench)")] = ...,
	server: Annotated[str, typer.Option("--server", help="Server name (required)")] = ...,
):
	session: CloudSession = ctx.obj
	try:
		options_url = _bench_options_url(session)
		options = session.get(options_url)
		frappe_source = _find_frappe_source(options, version)
		if not frappe_source:
			print_error(f"Could not find valid source for frappe in version '{version}'.")
			return
		_warn_server_name_format(server)
		_create_bench(session, title, version, region, frappe_source, server)
	except Exception as e:
		handle_exception(e, "Error creating bench group")


@deploy.command(help="Drop (archive) a bench group")
def drop_bench_group(
	ctx: typer.Context,
	name: Annotated[str, typer.Option("--name", help="Bench group name to drop/archive")] = ...,
):
	session: CloudSession = ctx.obj
	try:
		payload = {"doctype": "Release Group", "name": name}
		delete_url = _build_method_url(session, "press.api.client.delete")
		response = session.post(
			delete_url,
			json=payload,
			message=f"[bold red]Dropping bench group '{name}'...",
		)
		if response and response.get("exc_type"):
			print_error(f"Failed to drop bench group: {response.get('exception', 'Unknown error')}")
			return
		# Consider success if no error and either 'success' is True or no error but response is present
		if response.get("success") or (response and not response.get("exc_type")):
			print_success(f"Successfully dropped bench group: {name}")
		else:
			error_msg = response.get("message") or response.get("exception") or "Unknown error"
			print_error(f"Failed to drop bench group: {error_msg}")
	except Exception as e:
		handle_exception(e, "Error dropping bench group")


@deploy.command(help="Add app to bench group by name and version")
def add_app(
	ctx: typer.Context,
	bench: Annotated[str, typer.Option("--bench", help="Bench group name")] = ...,
	app: Annotated[str, typer.Option("--app", help="App name")] = ...,
	branch: Annotated[str, typer.Option("--branch", help="App branch (e.g. 'version-15-beta')")] = ...,
):
	session: CloudSession = ctx.obj
	url = _build_method_url(session, "press.api.bench.all_apps")
	payload = {"name": bench}
	try:
		response = session.post(url, json=payload)
		if not response or not isinstance(response, list):
			print_error("Failed to fetch apps list.")
			return
		source = _find_app_source(response, app, branch)
		if not source:
			print_error(f"Source not found for app '{app}' and branch '{branch}'")
			return
		add_url = _build_method_url(session, "press.api.bench.add_app")
		add_payload = {"name": bench, "source": source, "app": app}
		add_response = session.post(add_url, json=add_payload)
		if isinstance(add_response, dict):
			if add_response.get("success") or not add_response.get("exc_type"):
				print_success(f"Successfully added app '{app}' (branch '{branch}') to bench '{bench}'")
			else:
				error_msg = (
					add_response.get("message")
					or add_response.get("exception")
					or add_response.get("exc")
					or "Unknown error"
				)
				print_error(f"Failed to add app '{app}' to bench '{bench}': {error_msg}")
		elif isinstance(add_response, str):
			# Handle string response (e.g. when app is already added or not found)
			if "already exists" in add_response:
				print_info(f"App '{app}' is already added to bench '{bench}'.")
			else:
				print_error(f"Failed to add app '{app}' to bench '{bench}': {add_response}")
		else:
			print_error(f"Failed to add app '{app}' to bench '{bench}': Unknown error")
	except Exception as e:
		handle_exception(e, "Error adding app")


@deploy.command(help="Remove app from bench group")
def remove_app(
	ctx: typer.Context,
	bench: Annotated[str, typer.Option("--bench", help="Bench group name")] = ...,
	app: Annotated[str, typer.Option("--app", help="App name to remove")] = ...,
):
	session: CloudSession = ctx.obj
	url = _build_method_url(session, "press.api.client.run_doc_method")
	payload = {"dt": "Release Group", "dn": bench, "method": "remove_app", "args": {"app": app}}
	try:
		response = session.post(url, json=payload)
		if isinstance(response, dict):
			if response.get("success") or not response.get("exc_type"):
				print_success(f"Successfully removed app '{app}' from bench '{bench}'")
			else:
				error_msg = (
					response.get("message")
					or response.get("exception")
					or response.get("exc")
					or "Unknown error"
				)
				print_error(f"Failed to remove app '{app}' from bench '{bench}': {error_msg}")
		elif isinstance(response, str):
			# If response is just the app name, treat as success (already removed or not present)
			if response.strip() == app:
				print_success(f"Successfully removed app '{app}' from bench '{bench}'")
			elif "not found" in response or "does not exist" in response:
				print_info(f"App '{app}' is not present in bench '{bench}'.")
			else:
				print_error(f"Failed to remove app '{app}' from bench '{bench}': {response}")
		else:
			print_error(f"Failed to remove app '{app}' from bench '{bench}': Unknown error")
	except Exception as e:
		handle_exception(e, "Error removing app")


if __name__ == "__main__":
	pass

# --------------------
# Internal helpers (no behavior change, reduce complexity)
# --------------------


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
		print_error("Warning: Server name contains trailing backslash or spaces. Please check your input.")


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
			print_success(f"Successfully created bench group: {title}")
		elif isinstance(response, dict):
			print_error(f"Failed to create bench group: {response}")
		elif isinstance(response, str):
			print_success(f"Successfully created bench group: {response}")
		else:
			print_error(f"Backend error: {response}")
	except Exception as req_exc:
		handle_exception(req_exc, "Request error")
		if hasattr(req_exc, "response") and req_exc.response is not None:
			print_error(f"Backend response: {req_exc.response.text}")


def _bench_options_url(session: "CloudSession") -> str:
	"""Build bench options URL from session.base_url consistently."""
	return _build_method_url(session, "press.api.bench.options")


def _build_method_url(session: "CloudSession", method: str) -> str:
	"""Build a full URL to an API method using the session's base URL."""
	base_url = session.base_url.rstrip("/")
	if base_url.endswith("/api/method"):
		base_url = base_url[: -len("/api/method")]
	return f"{base_url}/api/method/{method}"


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
