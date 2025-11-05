from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from fc.commands.utils import get_doctype, validate_server_name
from fc.printer import Print, print_full_plan_details, print_plan_details, show_usage
from rich.console import Console

if TYPE_CHECKING:
	from fc.authentication.session import CloudSession

server = typer.Typer(help="Server Commands")
console = Console()


@server.command(help="Show live usage for a server")
def usage(
	ctx: typer.Context,
	name: Annotated[str | None, typer.Option("--name", "-n", help="Server name")] = None,
):
	session: CloudSession = ctx.obj

	if not name:
		Print.info(console, "Please provide a server name using --name.")
		return

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


def _noop() -> None:
	"""Placeholder to keep file structure stable; helpers removed to simplify usage output."""
	...


@server.command(help="Show details about a specific plan for a server")
def show_plan(
	ctx: typer.Context,
	name: Annotated[str, typer.Option("--name", "-n", help="Server name")] = ...,
	plan: Annotated[str, typer.Option("--plan", "-p", help="Plan name")] = ...,
):
	session: CloudSession = ctx.obj

	try:
		doctype = get_doctype(name)
		payload = {"name": doctype, "cluster": "Mumbai", "platform": "arm64"}

		plans = session.post(
			"press.api.server.plans", json=payload, message="[bold green]Fetching available server plans..."
		)

		selected_plan = next((p for p in plans if p.get("name") == plan), None)
		if not selected_plan:
			Print.error(console, f"Plan '{plan}' not found for server '{name}'")
			return

		console.print("[bold]Plan Details:[/bold]")
		console.print(f"[bold]Name:[/bold] [bold]{selected_plan.get('name', '-')}")
		console.print(f"[bold]Price:[/bold] [bold]₹{selected_plan.get('price_inr', '-')} /mo")
		console.print(
			f"[bold]vCPUs:[/bold] [bold]{selected_plan.get('vcpu', '-')}\n[bold]Memory:[/bold] [bold]{selected_plan.get('memory', '-')} GB\n[bold]Disk:[/bold] [bold]{selected_plan.get('disk', '-')} GB"
		)

	except Exception as e:
		Print.error(console, e)


@server.command(help="Shows the current plan for a server")
def server_plan(
	ctx: typer.Context,
	name: Annotated[str, typer.Option("--name", "-n", help="Server name")] = ...,
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
	name: Annotated[str, typer.Option("--name", "-n", help="Server name")] = ...,
	increment: Annotated[int, typer.Option("--increment", "-i", help="Increment size in GB")] = ...,
):
	session: CloudSession = ctx.obj
	is_valid, err = validate_server_name(name)
	if not is_valid:
		Print.error(console, err)
		return

	try:
		doctype = get_doctype(name)

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
	name: Annotated[str, typer.Option("--name", "-n", help="Name of the server")] = ...,
	plan: Annotated[str, typer.Option("--plan", "-o", help="Name of the plan")] = ...,
):
	session: CloudSession = ctx.obj

	try:
		doctype = get_doctype(name)
		payload = {"name": doctype, "cluster": "Mumbai", "platform": "arm64"}
		plans = session.post(
			"press.api.server.plans", json=payload, message="[bold green]Fetching available server plans..."
		)

		selected_plan = next((p for p in plans if p.get("name") == plan), None)
		if not selected_plan:
			Print.error(console, f"Plan '{plan}' not found for server '{name}'")
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

		print_plan_details(selected_plan, console)

	except Exception as e:
		Print.error(console, e)


@server.command(help="Create a new server")
def create_server(
	ctx: typer.Context,
	cluster: Annotated[str, typer.Option("--cluster", help="Cluster name")] = ...,
	title: Annotated[str, typer.Option("--title", help="Server title")] = ...,
	app_plan: Annotated[str, typer.Option("--app-plan", help="App server plan name")] = ...,
	db_plan: Annotated[str, typer.Option("--db-plan", help="Database server plan name")] = ...,
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
	name: Annotated[str, typer.Option("--name", help="Name of the server to delete")] = ...,
):
	session: CloudSession = ctx.obj

	try:
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
