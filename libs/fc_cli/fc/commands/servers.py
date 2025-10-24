from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from fc.commands.utils import (
	get_doctype,
	handle_exception,
	print_error,
	print_full_plan_details,
	print_info,
	print_success,
	validate_server_name,
)

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
		print_info("Please provide a server name using --name.")
		return

	try:
		usage_data = session.post(
			"press.api.server.usage",
			json={"name": name},
			message=f"[bold green]Fetching usage for {name}...",
		)

		console.print("[bold cyan]Usage (latest sample)[/bold cyan]")
		if not isinstance(usage_data, dict) or not usage_data:
			print_info("No usage data returned.")
			return

		vcpu = usage_data.get("vcpu")
		disk_gb = usage_data.get("disk")  # GB
		mem_mb = usage_data.get("memory")  # MB
		free_mem_bytes = usage_data.get("free_memory")  # bytes (avg 10m)

		console.print(
			f"[bold]vCPU:[/bold] {vcpu:.2f}"
			if isinstance(vcpu, (int, float))
			else f"[bold]vCPU:[/bold] {vcpu}"
		)
		console.print(
			f"[bold]Memory Used:[/bold] {mem_mb:.0f} MB"
			if isinstance(mem_mb, (int, float))
			else f"[bold]Memory Used:[/bold] {mem_mb}"
		)
		console.print(
			f"[bold]Disk Used:[/bold] {disk_gb:.0f} GB"
			if isinstance(disk_gb, (int, float))
			else f"[bold]Disk Used:[/bold] {disk_gb}"
		)
		console.print(
			f"[bold]Free Memory (avg 10m):[/bold] {free_mem_bytes / 1024 / 1024:.0f} MB"
			if isinstance(free_mem_bytes, (int, float))
			else f"[bold]Free Memory (avg 10m):[/bold] {free_mem_bytes}"
		)

	except Exception as e:
		handle_exception(e, "Error getting server usage")


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
			print_error(f"Plan '{plan}' not found for server '{name}'")
			return

		console.print("[bold]Plan Details:[/bold]")
		console.print(f"[bold]Name:[/bold] [bold]{selected_plan.get('name', '-')}")
		console.print(f"[bold]Price:[/bold] [bold]₹{selected_plan.get('price_inr', '-')} /mo")
		console.print(
			f"[bold]vCPUs:[/bold] [bold]{selected_plan.get('vcpu', '-')}\n[bold]Memory:[/bold] [bold]{selected_plan.get('memory', '-')} GB\n[bold]Disk:[/bold] [bold]{selected_plan.get('disk', '-')} GB"
		)

	except Exception as e:
		handle_exception(e, "Error fetching plan details")


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
			print_error(f"{doctype} '{name}' or its current plan not found.")
			return
		plan = response["current_plan"]
		print_full_plan_details(plan, console)
	except Exception as e:
		handle_exception(e, "Error getting server plan")


@server.command(help="Increase storage for a server")
def increase_storage(
	ctx: typer.Context,
	name: Annotated[str, typer.Option("--name", "-n", help="Server name")] = ...,
	increment: Annotated[int, typer.Option("--increment", "-i", help="Increment size in GB")] = ...,
):
	session: CloudSession = ctx.obj
	is_valid, err = validate_server_name(name)
	if not is_valid:
		print_error(err)
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
			print_error(f"Failed to increase storage: {response.get('message', 'Unknown error')}")
			return

		console.print(
			f"Storage increased for server [bold blue]{name}[/bold blue] by [bold blue]{increment}[/bold blue] GB",
			style="bold",
		)

	except Exception as e:
		handle_exception(e, "Error increasing storage")


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
			print_error(f"Plan '{plan}' not found for server '{name}'")
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
			print_error(f"Failed to change plan: {response.get('message', 'Unknown error')}")
			return

		console.print("[bold]Successfully changed plan![/bold]")
		console.print("[bold]Plan Details:[/bold]")
		console.print(f"[bold]Name:[/bold] [bold]{selected_plan.get('name', '-')}")
		console.print(f"[bold]Price:[/bold] [bold]₹{selected_plan.get('price_inr', '-')} /mo")
		console.print(f"[bold]vCPUs:[/bold] [bold]{selected_plan.get('vcpu', '-')}")
		console.print(f"[bold]Memory:[/bold] [bold]{selected_plan.get('memory', '-')} GB")
		console.print(f"[bold]Disk:[/bold] [bold]{selected_plan.get('disk', '-')} GB")

	except Exception as e:
		handle_exception(e, "Error changing plan")


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
			print_error(
				f"Failed to create server: {response.get('message', 'Unknown error') if response else 'No response from backend.'}"
			)
			return

		print_success(f"Successfully created server: {response['server']}")
		if response.get("job"):
			print_info(f"Job started: {response['job']}")

	except Exception as e:
		handle_exception(e, "Error creating server")


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
			print_error(f"Failed to delete server: {response.get('exception', 'Unknown error')}")
			return

		print_success(f"Successfully deleted (archived) server: {name}")

	except Exception as e:
		handle_exception(e, "Error deleting server")
