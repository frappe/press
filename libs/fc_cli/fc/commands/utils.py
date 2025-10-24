from __future__ import annotations

from typing import TYPE_CHECKING, Any

import typer

if TYPE_CHECKING:
	# Type-only import to avoid runtime dependency
	from rich.console import Console


def print_error(msg: str) -> None:
	"""Print an error message in red."""
	typer.secho(msg, fg="red")


def print_success(msg: str) -> None:
	"""Print a success message in green."""
	typer.secho(msg, fg="green")


def print_info(msg: str) -> None:
	"""Print an info message in cyan."""
	typer.secho(msg, fg="cyan")


def handle_exception(e: Exception, prefix: str = "Error") -> None:
	"""Standard exception printer to keep outputs consistent."""
	typer.secho(f"{prefix}: {e!s}", fg="red")


def print_plan_details(plan: dict[str, Any], console: "Console") -> None:
	"""Pretty-print plan details using a rich Console instance."""
	console.print("[bold]Plan Details:[/bold]")
	console.print(f"[bold]Name:[/bold] [bold]{plan.get('name', '-')}")
	console.print(f"[bold]Price:[/bold] [bold]₹{plan.get('price_inr', '-')} /mo")
	console.print(f"[bold]vCPUs:[/bold] [bold]{plan.get('vcpu', '-')}")
	console.print(f"[bold]Memory:[/bold] [bold]{plan.get('memory', '-')} GB")
	console.print(f"[bold]Disk:[/bold] [bold]{plan.get('disk', '-')} GB")


def print_full_plan_details(plan: dict[str, Any], console: "Console") -> None:
	"""Print an extended set of plan fields like title, owner, prices, etc."""
	console.print("[bold cyan]Current Plan[/bold cyan]")
	console.print(f"[bold]Title:[/bold] {plan.get('title', '-')}")
	console.print(f"[bold]Name:[/bold] {plan.get('name', '-')}")
	console.print(f"[bold]Owner:[/bold] {plan.get('owner', '-')}")
	console.print(f"[bold]Modified By:[/bold] {plan.get('modified_by', '-')}")
	console.print(f"[bold]Price INR:[/bold] {plan.get('price_inr', '-')}")
	console.print(f"[bold]Price USD:[/bold] {plan.get('price_usd', '-')}")
	console.print(f"[bold]Premium:[/bold] {plan.get('premium', '-')}")
	console.print(f"[bold]Price/Day INR:[/bold] {plan.get('price_per_day_inr', '-')}")
	console.print(f"[bold]Price/Day USD:[/bold] {plan.get('price_per_day_usd', '-')}")


def get_doctype(name: str) -> str:
	"""Infer doctype from a server name."""
	return "Server" if name and name.startswith("f") else "Database Server"


def validate_server_name(name: str) -> tuple[bool, str | None]:
	"""Validate server name format. Returns (is_valid, error_message)."""
	if not name:
		return False, "Server name is required"
	if not name.endswith("frappe.cloud"):
		return False, "Invalid server name. It must end with 'frappe.cloud'"
	return True, None
