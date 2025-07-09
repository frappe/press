import typing

if typing.TYPE_CHECKING:
	from rich.console import Console

	from fc.authentication.session import CloudSession


def server_usage(server: str, session: "CloudSession", console: "Console"):
	"""Show server usages"""
	usage = session.post("press.api.server.usage", json={"name": server})
	free_memory_gb = usage["free_memory"] / (1024**3)
	console.print("[bold cyan]Resource Usage[/bold cyan]")
	console.print(f"[bold]vCPU:[/bold] {usage['vcpu']}")
	console.print(f"[bold]Disk:[/bold] {usage['disk']} GB")
	console.print(f"[bold]Memory:[/bold] {usage['memory']} MB")
	console.print(f"[bold]Free Memory:[/bold] {free_memory_gb:.2f} GB")
