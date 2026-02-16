from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from fc.printer import Print

if TYPE_CHECKING:
	from fc.authentication.session import CloudSession

sites = typer.Typer(help="Sites Commands")
console = Console()

DOMAIN = "m.frappe.cloud"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get_session(ctx: typer.Context) -> "CloudSession | None":
	"""Get session from context, return None if invalid."""
	session = getattr(ctx, "obj", None)
	if session and hasattr(session, "post"):
		return session
	Print.error(console, "No session. Run: press-cli auth login <email>")
	return None


def _is_success(result: object) -> bool:
	"""Check if API result indicates success."""
	if isinstance(result, str):
		return bool(result)
	if isinstance(result, dict):
		return bool(result.get("success") or not result.get("exc_type"))
	return False


def _error_msg(result: object) -> str:
	"""Extract error message from API result."""
	if isinstance(result, dict):
		return str(result.get("message") or result.get("exception") or result) or "Unknown error"
	return str(result) or "Unknown error"


def _get_plans(session: "CloudSession") -> list[str]:
	"""Fetch available site plans."""
	resp = session.post("press.api.site.get_site_plans", json={}) or []
	items = resp if isinstance(resp, list) else resp.get("message", []) if isinstance(resp, dict) else []
	return [name for p in items if isinstance(p, dict) and (name := p.get("name")) is not None]


def _run_doc_method(
	session: "CloudSession",
	site: str,
	method: str,
	args: dict,
	message: str = "",
) -> dict | None:
	"""Call press.api.client.run_doc_method for a Site."""
	return session.post(
		"press.api.client.run_doc_method",
		json={"dt": "Site", "dn": site, "method": method, "args": args},
		message=message or None,
	)


def _print_backend_http_error(err: Exception) -> None:
	resp = getattr(err, "response", None)
	if resp is None:
		return
	status = getattr(resp, "status_code", None)
	url = getattr(resp, "url", None)
	Print.error(console, f"Backend HTTP error: {status} for url: {url}")
	try:
		Print.info(console, f"Backend response JSON: {resp.json()!r}")
	except Exception:
		text = getattr(resp, "text", "")
		Print.info(console, f"Backend response text: {text}")


def _is_duplicate_entry_http_error(err: Exception) -> bool:
	text = str(getattr(getattr(err, "response", None), "text", ""))
	return "DuplicateEntryError" in text


def _find_bench_info(benches: object, bench_name: str) -> dict | None:
	if not isinstance(benches, list):
		return None
	for bench in benches:
		if isinstance(bench, dict) and bench.get("name") == bench_name:
			return bench
	return None


# ─────────────────────────────────────────────────────────────────────────────
# Site Commands
# ─────────────────────────────────────────────────────────────────────────────


@sites.command(help="Provision a new site")
def new(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Site subdomain")],
	bench: Annotated[str, typer.Option("--bench", help="Bench group name")],
	plan: Annotated[str, typer.Option("--plan", help="Site plan")],
	apps: Annotated[list[str], typer.Option("--apps", help="Apps to install")],
) -> None:
	"""Create a new site on a bench."""
	session: CloudSession = ctx.obj
	full_site = f"{name}.{DOMAIN}"

	# Validate bench
	benches = session.get("press.api.bench.all") or []
	bench_names: list[str] = [
		str(name) for b in benches if isinstance(b, dict) and (name := b.get("name")) is not None
	]
	if bench not in bench_names:
		Print.error(console, f"Bench '{bench}' not found. Available: {', '.join(bench_names) or 'none'}")
		return

	# Fetch bench group server and its cluster
	bench_details = session.post(
		"press.api.client.get",
		json={"doctype": "Release Group", "name": bench, "fields": ["server"]},
		message="[bold green]Fetching bench group details...",
	)
	server_name = bench_details.get("server") if isinstance(bench_details, dict) else None
	cluster = None
	if server_name:
		server_details = session.post(
			"press.api.client.get",
			json={"doctype": "Server", "name": server_name, "fields": ["cluster"]},
			message="[bold green]Fetching server cluster...",
		)
		cluster = server_details.get("cluster") if isinstance(server_details, dict) else None
	Print.info(console, f"Bench group '{bench}' -> server={server_name!r}, cluster={cluster!r}")

	# Validate plan
	if plan not in (available := _get_plans(session)):
		Print.error(console, f"Invalid plan '{plan}'. Available: {', '.join(available)}")
		return

	payload: dict[str, object] = {
		"apps": apps or [],
		"cluster": cluster,  # Include cluster to avoid backend defaulting to Press Settings
		"domain": DOMAIN,
		"group": bench,
		"localisation_country": None,
		"name": name,
		"plan": plan,
		"selected_app_plans": {},
		"share_details_consent": False,
	}

	try:
		result = session.post(
			"press.api.site.new",
			json={"site": payload},
			message=f"[bold green]Provisioning '{full_site}'…",
		)
		if _is_success(result):
			Print.success(console, f"Site '{full_site}' created with apps: {', '.join(apps) or 'none'}")
		elif isinstance(result, dict) and result.get("exc_type") == "DuplicateEntryError":
			Print.error(console, f"Site '{full_site}' already exists.")
		else:
			Print.error(console, f"Failed: {_error_msg(result)}")
	except Exception as e:
		_print_backend_http_error(e)
		if _is_duplicate_entry_http_error(e):
			Print.error(console, f"Site '{full_site}' already exists.")
		else:
			Print.error(console, f"Error: {e}")


@sites.command(help="Archive (drop) a site")
def drop(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Site subdomain (without domain)")],
	force: Annotated[bool, typer.Option("--force", "-f", is_flag=True, help="Skip confirmation")] = False,
) -> None:
	"""Archive a site permanently."""
	session: CloudSession = ctx.obj
	full_site = f"{name}.{DOMAIN}"

	if not force and not typer.confirm(f"Archive '{full_site}'? This may be irreversible.", default=False):
		Print.info(console, "Cancelled.")
		return

	try:
		result = _run_doc_method(
			session,
			full_site,
			"archive",
			{"force": None},
			message=f"[bold red]Archiving '{full_site}'…",
		)
		if _is_success(result):
			Print.success(console, f"Site '{full_site}' archived.")
		else:
			Print.error(console, f"Failed: {_error_msg(result)}")
	except Exception as e:
		Print.error(console, f"Error: {e}")


@sites.command(help="Install available app(s) on a site")
def install_app(
	ctx: typer.Context,
	site: Annotated[str, typer.Argument(help="Full site domain")],
	app: Annotated[list[str] | None, typer.Option("--app", help="App(s) to install; omit for all")] = None,
) -> None:
	"""Install one or more apps on a site."""
	session: CloudSession = ctx.obj

	try:
		resp = session.get("press.api.site.available_apps", params={"name": site}) or []
		available = [x.get("app") for x in (resp if isinstance(resp, list) else []) if x.get("app")]

		if not available:
			Print.info(console, f"No apps available for '{site}'.")
			return

		targets = [a for a in (app or available) if a in available]
		if not targets:
			Print.info(console, "Nothing to install.")
			return

		for app_name in targets:
			result = _run_doc_method(session, site, "install_app", {"app": app_name})
			if _is_success(result):
				Print.success(console, f"Installed '{app_name}'")
			else:
				Print.error(console, f"Failed '{app_name}': {_error_msg(result)}")
	except Exception as e:
		Print.error(console, f"Error: {e}")


@sites.command(help="Uninstall an app from a site")
def uninstall_app(
	ctx: typer.Context,
	site: Annotated[str, typer.Argument(help="Full site domain")],
	app: Annotated[str, typer.Option("--app", help="App to uninstall")],
) -> None:
	"""Remove an app from a site."""
	session: CloudSession = ctx.obj

	try:
		result = _run_doc_method(
			session,
			site,
			"uninstall_app",
			{"app": app},
			message=f"[bold red]Uninstalling '{app}'…",
		)
		if _is_success(result):
			Print.success(console, f"Uninstalled '{app}' from '{site}'.")
		else:
			Print.error(console, f"Failed: {_error_msg(result)}")
	except Exception as e:
		Print.error(console, f"Error: {e}")


@sites.command(help="Schedule a backup")
def backup(
	ctx: typer.Context,
	site: Annotated[str, typer.Argument(help="Full site domain")],
	with_files: Annotated[bool, typer.Option("--with-files/--no-files", help="Include files")] = True,
	physical: Annotated[bool, typer.Option("--physical/--logical", help="Backup type")] = False,
	force: Annotated[bool, typer.Option("--force", "-f", is_flag=True, help="Skip confirmation")] = False,
) -> None:
	"""Schedule a site backup."""
	if not (session := _get_session(ctx)):
		return

	opts = f"files={'yes' if with_files else 'no'}, physical={'yes' if physical else 'no'}"
	if not force and not typer.confirm(f"Schedule backup for '{site}'? ({opts})", default=False):
		Print.info(console, "Cancelled.")
		return

	try:
		result = _run_doc_method(
			session,
			site,
			"schedule_backup",
			{"with_files": with_files, "physical": physical},
			message="[bold green]Scheduling backup…",
		)
		if _is_success(result):
			Print.success(console, f"Backup scheduled for '{site}'.")
		else:
			Print.error(console, f"Failed: {_error_msg(result)}")
	except Exception as e:
		Print.error(console, f"Error: {e}")


# ───────────────────────────────────────────────────────────
# Bench Group Commands
# ───────────────────────────────────────────────────────────


def _do_switch_group(session: "CloudSession", site: str, groups: list) -> None:
	"""Switch site to an existing bench group."""
	if len(groups) == 1:
		target = groups[0]
	else:
		idx = typer.prompt(f"Enter group number (1-{len(groups)})", default="1")
		try:
			target = groups[int(idx) - 1]
		except (ValueError, IndexError):
			Print.error(console, "Invalid selection.")
			return

	skip = typer.confirm("Skip failing patches?", default=False)
	try:
		session.post(
			"press.api.site.change_group",
			json={"name": site, "group": target.get("name"), "skip_failing_patches": skip},
			message=f"[bold green]Switching to '{target.get('title')}'…",
		)
		Print.success(console, f"Moved to '{target.get('title')}'.")
	except Exception as e:
		Print.error(console, f"Error: {e}")


def _do_clone_group(session: "CloudSession", site: str) -> None:
	"""Clone current bench group to a new one."""
	title = typer.prompt("New bench group title")
	if not title:
		Print.error(console, "Title required.")
		return

	try:
		result = session.post(
			"press.api.site.clone_group",
			json={"name": site, "new_group_title": title},
			message=f"[bold green]Cloning bench as '{title}'…",
		)
		bench = result.get("bench_name") if isinstance(result, dict) else None
		if bench:
			Print.success(console, f"Cloned to '{bench}'. Build started.")
		else:
			Print.error(console, f"Clone failed: {result}")
	except Exception as e:
		Print.error(console, f"Error: {e}")


def _show_move_menu(groups: list) -> None:
	"""Display the move group menu options."""
	console.print("\n[bold]Move Site to another Bench Group[/bold]\n")

	if groups:
		console.print(f"Found {len(groups)} bench group(s):\n")
		for i, g in enumerate(groups, 1):
			console.print(f"  {i}. {g.get('title', g.get('name'))} ({g.get('name')})")
	else:
		console.print("No other bench groups available. You can clone this one.\n")

	console.print("\n[bold]Options:[/bold]")
	if groups:
		console.print("  1. Change Bench Group")
	console.print("  2. Clone current Bench Group")
	console.print("  0. Cancel\n")


def _handle_move_choice(session: "CloudSession", site: str, groups: list, choice: str) -> None:
	"""Route menu choice to appropriate handler."""
	if choice == "1" and groups:
		_do_switch_group(session, site, groups)
	elif choice == "2":
		_do_clone_group(session, site)
	elif choice == "0":
		Print.info(console, "Cancelled.")
	else:
		Print.error(console, "Invalid option.")


@sites.command(help="Move site to another bench group")
def move_group(
	ctx: typer.Context,
	site: Annotated[str, typer.Argument(help="Full site domain")],
) -> None:
	"""Interactive menu to switch or clone bench group."""
	if not (session := _get_session(ctx)):
		return

	try:
		options = session.post("press.api.site.change_group_options", json={"name": site})
	except Exception as e:
		Print.error(console, f"Error fetching options: {e}")
		return

	groups = options if isinstance(options, list) else []
	_show_move_menu(groups)
	_handle_move_choice(session, site, groups, typer.prompt("Select option", default="0"))
