from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from fc.commands.utils import get_doctype, validate_server_name
from fc.printer import Print, print_full_plan_details, print_plan_details, show_usage

if TYPE_CHECKING:
	from fc.authentication.session import CloudSession

server = typer.Typer(help="Server Commands")
console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


def _should_proceed(message: str, force: bool) -> bool:
	"""Prompt user for confirmation unless force is True."""
	return force or typer.confirm(message, default=False)


def _get_current_plan_name(session: "CloudSession", doctype: str, name: str) -> str | None:
	"""Fetch and return the current plan name for a server."""
	resp = session.post(
		"press.api.client.get",
		json={"doctype": doctype, "name": name, "fields": ["current_plan"], "debug": 0},
		message="[bold green]Checking current server plan...",
	)
	if not isinstance(resp, dict):
		return None
	cp = resp.get("current_plan")
	if isinstance(cp, dict):
		return cp.get("name")
	return cp if isinstance(cp, str) else None


def _find_plan(plans: list[dict], plan_name: str) -> dict | None:
	"""Find a plan by name from a list of plans."""
	return next((p for p in plans if p.get("name") == plan_name), None)


def _normalize_plans_response(plans_resp: object) -> list[dict] | None:
	"""Accept both list and wrapped dict responses from the backend."""
	if isinstance(plans_resp, list):
		return plans_resp
	if isinstance(plans_resp, dict) and isinstance(plans_resp.get("plans"), list):
		return plans_resp["plans"]
	return None


def _get_server_cluster_platform(
	session: "CloudSession",
	doctype: str,
	name: str,
) -> tuple[str | None, str | None]:
	resp = session.post(
		"press.api.client.get",
		json={
			"doctype": doctype,
			"name": name,
			"fields": ["cluster", "platform", "current_plan"],
			"debug": 0,
		},
		message="[bold green]Getting server metadata...",
	)
	if not isinstance(resp, dict):
		return None, None

	cluster = resp.get("cluster")
	platform = resp.get("platform")
	current_plan = resp.get("current_plan")
	if isinstance(current_plan, dict):
		cluster = cluster or current_plan.get("cluster")
		platform = platform or current_plan.get("platform")

	return (cluster if isinstance(cluster, str) else None, platform if isinstance(platform, str) else None)


def _build_plans_request(doctype: str, cluster: str | None, platform: str | None) -> dict[str, str]:
	request: dict[str, str] = {"name": doctype}
	if cluster:
		request["cluster"] = cluster
	if platform:
		request["platform"] = platform
	return request


def _validate_in_list(value: str, available: list[str], label: str) -> str | None:
	"""Return error message if value not in available list, else None."""
	if value not in available:
		return f"{label} '{value}' is not available."
	return None


# ─────────────────────────────────────────────────────────────────────────────
# Server Commands
# ─────────────────────────────────────────────────────────────────────────────


@server.command(help="Show live usage for a server")
def usage(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name")],
):
	session: CloudSession = ctx.obj
	try:
		data = session.post(
			"press.api.server.usage",
			json={"name": name},
			message=f"[bold green]Fetching usage for {name}...",
		)
		if not isinstance(data, dict):
			Print.error(
				console, f"Backend returned unexpected response (usage): {type(data).__name__}: {data!r}"
			)
			return
		if not isinstance(data, dict) or not data:
			Print.info(console, "No usage data returned.")
			return

		show_usage(
			vcpu=data.get("vcpu"),
			mem_mb=data.get("memory"),
			disk_gb=data.get("disk"),
			free_mem_bytes=data.get("free_memory"),
			console=console,
		)
	except Exception as e:
		Print.error(console, e)


@server.command(help="Show details about a specific plan for a server")
def show_plan(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name")],
	plan: Annotated[str, typer.Option("--plan", help="Plan name")],
):
	session: CloudSession = ctx.obj
	try:
		doctype = get_doctype(name)
		cluster, platform = _get_server_cluster_platform(session, doctype, name)
		plans_request = _build_plans_request(doctype, cluster, platform)
		plans_resp = session.post(
			"press.api.server.plans",
			json=plans_request,
			message="[bold green]Fetching available server plans...",
		)
		plans = _normalize_plans_response(plans_resp)
		if plans is None:
			Print.error(
				console,
				f"Backend returned unexpected response (plans): {type(plans_resp).__name__}: {plans_resp!r}",
			)
			return
		selected = _find_plan(plans, plan)
		if not selected:
			plan_names = [
				p.get("name") for p in plans if isinstance(p, dict) and isinstance(p.get("name"), str)
			]
			Print.info(console, f"Debug: plans request: {plans_request!r}")
			if isinstance(plans_resp, dict):
				Print.info(console, f"Debug: plans response keys: {sorted(plans_resp.keys())}")
			else:
				Print.info(console, f"Debug: plans response type: {type(plans_resp).__name__}")
			Print.info(console, f"Debug: normalized plans count: {len(plan_names)}")
			Print.info(console, f"Debug: first plan names: {plan_names[:10]}")
			needle_family = plan.split("-", 1)[0]
			candidates = [n for n in plan_names if n is not None and needle_family and needle_family in n]
			if candidates:
				Print.info(console, f"Debug: candidate plan names: {candidates[:10]}")
			Print.error(console, f"Plan '{plan}' not found for server '{name}'")
			return
		print_plan_details(selected, console)
	except Exception as e:
		Print.error(console, e)


@server.command(help="Shows the current plan for a server")
def server_plan(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name")],
):
	session: CloudSession = ctx.obj
	try:
		doctype = get_doctype(name)
		response = session.post(
			"press.api.client.get",
			json={"doctype": doctype, "name": name, "fields": ["current_plan"], "debug": 0},
			message="[bold green]Getting server details...",
		)
		if not isinstance(response, dict):
			Print.error(
				console,
				f"Backend returned unexpected response (client.get): {type(response).__name__}: {response!r}",
			)
			return
		if not response or "current_plan" not in response:
			Print.error(console, f"{doctype} '{name}' or its current plan not found.")
			return
		print_full_plan_details(response["current_plan"], console)
	except Exception as e:
		Print.error(console, e)


@server.command(help="Increase storage for a server")
def increase_storage(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name")],
	increment: Annotated[int, typer.Option("--increment", help="Increment size in GB")],
	force: Annotated[bool, typer.Option("--force", "-f", is_flag=True, help="Skip confirmation")] = False,
):
	session: CloudSession = ctx.obj
	is_valid, err = validate_server_name(name)
	if not is_valid:
		Print.error(console, err)
		return

	try:
		doctype = get_doctype(name)
		if not _should_proceed(
			f"Increase storage for server '{name}' by {increment} GB? This action may be irreversible.",
			force,
		):
			Print.info(console, "Operation cancelled.")
			return

		response = session.post(
			"press.api.client.run_doc_method",
			json={
				"dt": doctype,
				"dn": name,
				"method": "increase_disk_size_for_server",
				"args": {"server": name, "increment": increment},
			},
			message=f"[bold green]Increasing storage for {name} by {increment}GB...",
		)
		Print.info(console, f"Debug: backend response: {response!r}")
		if not isinstance(response, dict):
			Print.error(
				console,
				f"Backend returned unexpected response (run_doc_method): {type(response).__name__}: {response!r}",
			)
			return
		if response.get("success") is False:
			Print.error(console, f"Failed to increase storage: {response.get('message', 'Unknown error')}")
			return
		Print.success(console, f"Storage increased for server {name} by {increment} GB")
	except Exception as e:
		resp = getattr(e, "response", None)
		if resp is None:
			Print.error(console, e)
			return

		status = getattr(resp, "status_code", None)
		url = getattr(resp, "url", None)
		Print.error(console, f"Backend HTTP error: {status} for url: {url}")
		try:
			Print.info(console, f"Backend response JSON: {resp.json()!r}")
		except Exception:
			text = getattr(resp, "text", "")
			Print.info(console, f"Backend response text: {text}")


@server.command(help="Change the plan for a server")
def choose_plan(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name")],
	plan: Annotated[str, typer.Option("--plan", help="Plan name")],
	force: Annotated[bool, typer.Option("--force", "-f", is_flag=True, help="Skip confirmation")] = False,
):
	session: CloudSession = ctx.obj
	try:
		doctype = get_doctype(name)
		cluster, platform = _get_server_cluster_platform(session, doctype, name)
		plans_request = _build_plans_request(doctype, cluster, platform)
		plans_resp = session.post(
			"press.api.server.plans",
			json=plans_request,
			message="[bold green]Fetching available server plans...",
		)
		plans = _normalize_plans_response(plans_resp)
		if plans is None:
			Print.error(
				console,
				f"Backend returned unexpected response (plans): {type(plans_resp).__name__}: {plans_resp!r}",
			)
			return

		selected = _find_plan(plans, plan)
		if not selected:
			Print.error(console, f"Plan '{plan}' not found for server '{name}'")
			return

		current_plan_name = _get_current_plan_name(session, doctype, name)
		if current_plan_name == selected.get("name"):
			Print.info(console, f"Plan '{current_plan_name}' is already active. Choose a different plan.")
			return

		if not _should_proceed(f"Change plan for server '{name}' to '{selected.get('name')}'?", force):
			Print.info(console, "Operation cancelled.")
			return

		response = session.post(
			"press.api.client.run_doc_method",
			json={"dt": doctype, "dn": name, "method": "change_plan", "args": {"plan": selected.get("name")}},
			message=f"[bold green]Changing plan for {name} to {selected.get('name')}...",
		)
		if not isinstance(response, dict):
			Print.error(
				console,
				f"Backend returned unexpected response (run_doc_method): {type(response).__name__}: {response!r}",
			)
			return
		if response and response.get("success") is False:
			Print.error(console, f"Failed to change plan: {response.get('message', 'Unknown error')}")
			return

		Print.success(console, f"Plan changed: {current_plan_name or '(unknown)'} -> {selected.get('name')}")
		print_plan_details(selected, console)
	except Exception as e:
		Print.error(console, e)


@server.command(help="Create a new server")
def create_server(  # noqa: C901
	ctx: typer.Context,
	title: Annotated[str, typer.Argument(help="Server title")],
	cluster: Annotated[str, typer.Argument(help="Cluster name")],
	app_plan: Annotated[str, typer.Argument(help="App server plan name")],
	db_plan: Annotated[str | None, typer.Argument(help="Database server plan (optional for unified)")] = None,
	unified: Annotated[
		bool, typer.Option("--unified", "-u", is_flag=True, help="Create unified server")
	] = False,
	auto_increase_storage: Annotated[bool, typer.Option("--auto-increase-storage", is_flag=True)] = False,
	force: Annotated[bool, typer.Option("--force", "-f", is_flag=True, help="Skip confirmation")] = False,
):
	session: CloudSession = ctx.obj
	try:
		# Fetch and validate options
		options = session.post(
			"press.api.server.options",
			json={},
			message="[bold green]Fetching server options...",
		)
		if not isinstance(options, dict):
			Print.error(
				console,
				f"Backend returned unexpected response (server.options): {type(options).__name__}: {options!r}",
			)
			return
		if not options:
			Print.error(console, "Failed to fetch server options from the API.")
			return

		# Validate inputs
		regions: list[str] = [
			name
			for r in options.get("regions", [])
			if isinstance(r, dict) and (name := r.get("name")) is not None
		]
		app_plans_list = options.get("app_plans", [])
		app_plan_names: list[str] = [
			name for p in app_plans_list if isinstance(p, dict) and (name := p.get("name")) is not None
		]

		if err := _validate_in_list(cluster, regions, "Cluster"):
			Print.error(console, err)
			return
		if err := _validate_in_list(app_plan, app_plan_names, "App plan"):
			Print.error(console, err)
			return

		# Find the selected app plan to check allow_unified_server
		selected_app_plan = next((p for p in app_plans_list if p.get("name") == app_plan), None)
		allows_unified = selected_app_plan.get("allow_unified_server", 0) if selected_app_plan else 0

		if db_plan and unified:
			Print.error(console, "Cannot specify both --unified flag and a db_plan.")
			return
		if db_plan:
			db_plans = [p.get("name") for p in options.get("db_plans", [])]
			if err := _validate_in_list(db_plan, db_plans, "Database plan"):
				Print.error(console, err)
				return

		# Determine server type
		is_unified = unified or not db_plan

		# Check if unified is allowed for this plan
		if is_unified and not allows_unified:
			Print.error(
				console,
				f"Plan '{app_plan}' does not allow unified server creation. Please specify a db_plan.",
			)
			return

		if (
			not db_plan
			and not unified
			and not force
			and not typer.confirm("No database plan specified. Create a unified server?", default=True)
		):
			Print.info(console, "Operation cancelled.")
			return

		# Build payload and call API
		base_payload = {
			"cluster": cluster,
			"title": title,
			"app_plan": app_plan,
			"auto_increase_storage": auto_increase_storage,
		}

		if is_unified:
			Print.info(console, "Creating unified server...")
			response = session.post(
				"press.api.server.new_unified",
				json={"server": base_payload},
				message=f"[bold green]Creating unified server '{title}' in '{cluster}'...",
			)
		else:
			Print.info(console, "Creating separate servers...")
			response = session.post(
				"press.api.server.new",
				json={"server": {**base_payload, "db_plan": db_plan}},
				message=f"[bold green]Creating server '{title}' in '{cluster}'...",
			)

		if not isinstance(response, dict):
			Print.error(
				console,
				f"Backend returned unexpected response (server.new): {type(response).__name__}: {response!r}",
			)
			return

		if not response or not response.get("server"):
			msg = response.get("message", "Unknown error") if response else "No response from backend."
			Print.error(console, f"Failed to create server: {msg}")
			return

		Print.success(console, f"Successfully created server: {response['server']}")
		if response.get("job"):
			Print.info(console, f"Server creation job started: {response['job']}")
	except Exception as e:
		Print.error(console, e)


@server.command(help="Delete a server (archive)")
def delete_server(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name to delete")],
	force: Annotated[bool, typer.Option("--force", "-f", is_flag=True, help="Skip confirmation")] = False,
):
	session: CloudSession = ctx.obj
	try:
		if not _should_proceed(
			f"Are you sure you want to archive server '{name}'? This action may be irreversible.",
			force,
		):
			Print.info(console, "Operation cancelled.")
			return

		response = session.post(
			"press.api.server.archive",
			json={"name": name},
			message=f"[bold red]Archiving server '{name}'...",
		)
		if not isinstance(response, dict):
			Print.error(
				console,
				f"Backend returned unexpected response (server.archive): {type(response).__name__}: {response!r}",
			)
			return
		if response and response.get("exc_type"):
			Print.error(console, f"Failed to delete server: {response.get('exception', 'Unknown error')}")
			return
		Print.success(console, f"Successfully deleted (archived) server: {name}")
	except Exception as e:
		Print.error(console, e)
