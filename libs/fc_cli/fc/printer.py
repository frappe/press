from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
	from rich.console import Console


class Print:
	"""Class to handle print primitives"""

	@classmethod
	def info(cls, console: "Console", message: str, **kwargs) -> None:
		console.print(f"{message}", style="cyan", **kwargs)

	@classmethod
	def success(cls, console: "Console", message: str, **kwargs) -> None:
		console.print(f"✓ {message}", style="bold green", **kwargs)

	@classmethod
	def error(cls, console: "Console", message: str | Exception, **kwargs) -> None:
		console.print(f"✗ {message}", style="bold red", **kwargs)

	@classmethod
	def header(cls, console: "Console", title: str) -> None:
		"""Print a section header."""
		console.print(f"[bold cyan]{title}[/bold cyan]")

	@classmethod
	def field(cls, console: "Console", label: str, value: typing.Any, indent: int = 0) -> None:
		"""Print a labeled field with optional indentation."""
		spaces = "  " * indent
		console.print(f"{spaces}[bold]{label}:[/bold] {value}")


def print_plan_details(plan: dict[str, typing.Any], console: "Console") -> None:
	"""Pretty-print plan details using a rich Console instance."""
	Print.header(console, "Plan Details")
	Print.field(console, "Name", plan.get("name", "-"))
	Print.field(console, "Price", f"₹{plan.get('price_inr', '-')} /mo")
	Print.field(console, "vCPUs", plan.get("vcpu", "-"))
	Print.field(console, "Memory", f"{plan.get('memory', '-')} GB")
	Print.field(console, "Disk", f"{plan.get('disk', '-')} GB")


def print_full_plan_details(plan: dict[str, typing.Any], console: "Console") -> None:
	"""Print an extended set of plan fields like title, owner, prices, etc."""
	Print.header(console, "Current Plan")
	Print.field(console, "Title", plan.get("title", "-"))
	Print.field(console, "Name", plan.get("name", "-"))
	Print.field(console, "Owner", plan.get("owner", "-"))
	Print.field(console, "Modified By", plan.get("modified_by", "-"))
	Print.field(console, "Price INR", plan.get("price_inr", "-"))
	Print.field(console, "Price USD", plan.get("price_usd", "-"))
	Print.field(console, "Premium", plan.get("premium", "-"))
	Print.field(console, "Price/Day INR", plan.get("price_per_day_inr", "-"))
	Print.field(console, "Price/Day USD", plan.get("price_per_day_usd", "-"))


def show_usage(
	vcpu: str | float | int,
	mem_mb: str | float | int,
	disk_gb: str | float | int,
	free_mem_bytes: str | float | int,
	console: "Console",
) -> None:
	Print.header(console, "Server Usage")
	Print.field(console, "vCPU", f"{vcpu:.2f}" if isinstance(vcpu, (int, float)) else vcpu)
	Print.field(console, "Memory Used", f"{mem_mb:.0f} MB" if isinstance(mem_mb, (int, float)) else mem_mb)
	Print.field(console, "Disk Used", f"{disk_gb:.0f} GB" if isinstance(disk_gb, (int, float)) else disk_gb)
	Print.field(
		console,
		"Free Memory (avg 10m)",
		f"{free_mem_bytes / 1024 / 1024:.0f} MB"
		if isinstance(free_mem_bytes, (int, float))
		else free_mem_bytes,
	)
