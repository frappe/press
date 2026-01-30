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


@server.command(help="Show live usage for a server")
def usage(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name")],
):
	session: CloudSession = ctx.obj

	try:
		usage_data = session.post(
			"press.api.server.usage",
			json={"name": name},
			message=f"[bold green]Fetching usage for {name}...",
		)

		if not isinstance(usage_data, dict) or not usage_data:
			Print.info(console, "No usage data returned.")
			return

		vcpu = usage_data.get("vcpu")
		disk_gb = usage_data.get("disk")  # GB
		mem_mb = usage_data.get("memory")  # MB
		free_mem_bytes = usage_data.get("free_memory")  # bytes (avg 10m)

		show_usage(
			vcpu=vcpu,
			mem_mb=mem_mb,
			disk_gb=disk_gb,
			free_mem_bytes=free_mem_bytes,
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
		payload = {"name": doctype, "cluster": "Mumbai", "platform": "arm64"}

		plans = session.post(
			"press.api.server.plans", json=payload, message="[bold green]Fetching available server plans..."
		).get("plans", [])

		selected_plan = next((p for p in plans if p.get("name") == plan), None)
		if not selected_plan:
			Print.error(console, f"Plan '{plan}' not found for server '{name}'")
			return

		print_plan_details(selected_plan, console)

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
		payload = {
			"doctype": doctype,
			"name": name,
			"fields": ["current_plan"],
			"debug": 0,
		}
		response = session.post(
			"press.api.client.get", json=payload, message="[bold green]Getting server details..."
		)
		if not response or "current_plan" not in response:
			Print.error(console, f"{doctype} '{name}' or its current plan not found.")
			return
		plan = response["current_plan"]
		print_full_plan_details(plan, console)
	except Exception as e:
		Print.error(console, e)


@server.command(help="Increase storage for a server")
def increase_storage(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name")],
	increment: Annotated[int, typer.Option("--increment", help="Increment size in GB")],
	force: Annotated[
		bool,
		typer.Option("--force", "-f", is_flag=True, help="Skip confirmation"),
	] = False,
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

		payload = {
			"dt": doctype,
			"dn": name,
			"method": "increase_disk_size_for_server",
			"args": {"server": name, "increment": increment},
		}

		response = session.post(
			"press.api.client.run_doc_method",
			json=payload,
			message=f"[bold green]Increasing storage for {name} by {increment}GB...",
		)

		if response and response.get("success") is False:
			Print.error(console, f"Failed to increase storage: {response.get('message', 'Unknown error')}")
			return

		Print.success(
			console,
			f"Storage increased for server {name} by {increment} GB",
		)

	except Exception as e:
		Print.error(console, e)


@server.command(help="Show current plan and choose available server plans")
def choose_plan(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Server name")],
	plan: Annotated[str, typer.Option("--plan", help="Plan name")],
	force: Annotated[
		bool,
		typer.Option("--force", "-f", is_flag=True, help="Skip confirmation"),
	] = False,
):
	session: CloudSession = ctx.obj

	try:
		doctype = get_doctype(name)
		payload = {"name": doctype, "cluster": "Mumbai", "platform": "arm64"}
		plans = session.post(
			"press.api.server.plans", json=payload, message="[bold green]Fetching available server plans..."
		).get("plans", [])

		selected_plan = next((p for p in plans if p.get("name") == plan), None)
		if not selected_plan:
			Print.error(console, f"Plan '{plan}' not found for server '{name}'")
			return

		current_plan_name = _get_current_plan_name(session, doctype, name)

		if current_plan_name and current_plan_name == selected_plan.get("name"):
			Print.info(
				console,
				f"Plan '{current_plan_name}' is already active for server '{name}'. Choose a different plan to change.",
			)
			return

		if not _should_proceed(
			f"Change plan for server '{name}' to '{selected_plan.get('name')}'?",
			force,
		):
			Print.info(console, "Operation cancelled.")
			return

		change_payload = {
			"dt": doctype,
			"dn": name,
			"method": "change_plan",
			"args": {"plan": selected_plan.get("name")},
		}

		response = session.post(
			"press.api.client.run_doc_method",
			json=change_payload,
			message=f"[bold green]Changing plan for {name} to {selected_plan.get('name')}...",
		)

		if response and response.get("success") is False:
			Print.error(console, f"Failed to change plan: {response.get('message', 'Unknown error')}")
			return

		previous_plan = current_plan_name or "(unknown)"
		Print.success(
			console,
			f"Plan changed for server '{name}': {previous_plan} -> {selected_plan.get('name')}",
		)
		print_plan_details(selected_plan, console)

	except Exception as e:
		Print.error(console, e)


@server.command(help="Create a new server")
def create_server(
	ctx: typer.Context,
	title: Annotated[str, typer.Argument(help="Server title")],
	cluster: Annotated[str, typer.Option("--cluster", help="Cluster name")] = "",
	app_plan: Annotated[str, typer.Option("--app-plan", help="App server plan name")] = "",
	db_plan: Annotated[str, typer.Option("--db-plan", help="Database server plan name")] = "",
	auto_increase_storage: Annotated[
		bool, typer.Option("--auto-increase-storage", is_flag=True, help="Auto increase storage")
	] = False,
):
	session: CloudSession = ctx.obj

	try:
		server_payload = {
			"cluster": cluster,
			"title": title,
			"app_plan": app_plan,
			"db_plan": db_plan,
			"auto_increase_storage": auto_increase_storage,
		}

		response = session.post(
			"press.api.server.new",
			json={"server": server_payload},
			message=f"[bold green]Creating server '{title}' in cluster '{cluster}'...",
		)

		if not response or not response.get("server"):
			Print.error(
				console,
				f"Failed to create server: {response.get('message', 'Unknown error') if response else 'No response from backend.'}",
			)
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
	force: Annotated[
		bool,
		typer.Option("--force", "-f", is_flag=True, help="Skip confirmation"),
	] = False,
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

		if response and response.get("exc_type"):
			Print.error(console, f"Failed to delete server: {response.get('exception', 'Unknown error')}")
			return

		Print.success(console, f"Successfully deleted (archived) server: {name}")

	except Exception as e:
		Print.error(console, e)


def _should_proceed(message: str, confirm_token: str | None) -> bool:
	if isinstance(confirm_token, bool) and confirm_token:
		return True
	if isinstance(confirm_token, str) and confirm_token.lower() in {"force", "yes", "y"}:
		return True
	return typer.confirm(message, default=False)


def _get_current_plan_name(session: "CloudSession", doctype: str, name: str) -> str | None:
	resp = session.post(
		"press.api.client.get",
		json={
			"doctype": doctype,
			"name": name,
			"fields": ["current_plan"],
			"debug": 0,
		},
		message="[bold green]Checking current server plan...",
	)
	if isinstance(resp, dict) and resp.get("current_plan"):
		cp = resp["current_plan"]
		if isinstance(cp, dict):
			return cp.get("name")
		if isinstance(cp, str):
			return cp
	return None
