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
	def warn(cls, console: "Console", message: str, **kwargs) -> None:
		"""Non-fatal warning message."""
		console.print(f"! {message}", style="bold yellow", **kwargs)

	@classmethod
	def header(cls, console: "Console", title: str) -> None:
		"""Print a section header."""
		console.print(f"[bold cyan]{title}[/bold cyan]")

	@classmethod
	def field(cls, console: "Console", label: str, value: typing.Any, indent: int = 0) -> None:
		"""Print a labeled field with optional indentation."""
		spaces = "  " * indent
		console.print(f"{spaces}[bold]{label}:[/bold] {value}")

	@classmethod
	def code(cls, console: "Console", message: str, **kwargs) -> None:
		"""Simulate terminal color: gray text on black background."""
		console.print(f"{message}", style="grey0 on black", **kwargs)


def print_plan_details(plan: dict[str, typing.Any], console: "Console") -> None:
	"""Pretty-print plan details using a rich Console instance."""
	Print.header(console, "Plan Details")
	Print.field(console, "Name", plan.get("name", "-"))
	Print.field(console, "Price", f"{fmt_inr(plan.get('price_inr'))} /mo")
	Print.field(console, "vCPUs", fmt_cpu(plan.get("vcpu")))
	Print.field(console, "Memory", fmt_gb(plan.get("memory")))
	Print.field(console, "Disk", fmt_gb(plan.get("disk")))


def print_full_plan_details(plan: dict[str, typing.Any], console: "Console") -> None:
	"""Print an extended set of plan fields like title, owner, prices, etc."""
	Print.header(console, "Current Plan")
	Print.field(console, "Title", plan.get("title", "-"))
	Print.field(console, "Name", plan.get("name", "-"))
	Print.field(console, "Owner", plan.get("owner", "-"))
	Print.field(console, "Modified By", plan.get("modified_by", "-"))
	Print.field(console, "Price INR", fmt_inr(plan.get("price_inr")))
	Print.field(console, "Price USD", plan.get("price_usd", "-"))
	Print.field(console, "Premium", "Yes" if plan.get("premium") else "No")
	Print.field(console, "Price/Day INR", fmt_inr(plan.get("price_per_day_inr")))
	Print.field(console, "Price/Day USD", plan.get("price_per_day_usd", "-"))


def show_usage(
	vcpu: str | float | int,
	mem_mb: str | float | int,
	disk_gb: str | float | int,
	free_mem_bytes: str | float | int,
	console: "Console",
) -> None:
	Print.header(console, "Server Usage")
	Print.field(console, "vCPU", fmt_cpu(vcpu))
	Print.field(console, "Memory Used", fmt_mb(mem_mb))
	Print.field(console, "Disk Used", fmt_gb(disk_gb, 2))
	# free_mem_bytes is bytes; show as MB
	if isinstance(free_mem_bytes, (int, float)):
		free_mb = free_mem_bytes / 1024 / 1024
	else:
		free_mb = free_mem_bytes
	Print.field(console, "Free Memory (avg 10m)", fmt_mb(free_mb))


# ---------- formatting helpers ----------
def _fmt_number(value: typing.Any, decimals: int = 0) -> str:
	"""Format numbers with thousand separators and optional decimals; strip trailing zeros."""
	if isinstance(value, (int, float)):
		# Round to desired precision to avoid long floats like 2.826424479...
		rounded = round(float(value), decimals)
		if decimals > 0:
			return f"{rounded:,.{decimals}f}".rstrip("0").rstrip(".")
		return f"{int(rounded):,}"
	return str(value)


def fmt_gb(value: typing.Any, decimals: int = 0) -> str:
	if value is None or value == "-":
		return "-"
	return f"{_fmt_number(value, decimals)} GB"


def fmt_mb(value: typing.Any, decimals: int = 2) -> str:
	if value is None or value == "-":
		return "-"
	return f"{_fmt_number(value, decimals)} MB"


def fmt_cpu(value: typing.Any, decimals: int = 2) -> str:
	if value is None or value == "-":
		return "-"
	return _fmt_number(value, decimals)


def fmt_inr(value: typing.Any) -> str:
	if value is None or value == "-":
		return "-"
	return f"₹{_fmt_number(value, 0)}"
