from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

from fc.printer import Print

if TYPE_CHECKING:
	from fc.authentication.session import CloudSession


sites = typer.Typer(help="Sites Commands")
console = Console()


@sites.command(help="Provision a new site with multiple apps")
def new(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Site name/subdomain (name)")],
	bench_opt: Annotated[str, typer.Option("--bench", help="Bench group name (group)")],
	plan: Annotated[str, typer.Option("--plan", help="Plan (plan)")],
	apps: Annotated[list[str], typer.Option("--apps", help="Apps list (apps)")],
):
	"""Create a new site on a bench after checking availability."""
	session: CloudSession = ctx.obj

	benches = session.get("press.api.bench.all") or []
	bench_names = [b.get("name") for b in benches if isinstance(b, dict) and b.get("name")]
	if bench_opt in bench_names:
		bench = bench_opt
	else:
		Print.error(
			console,
			f"Bench '{bench_opt}' not found. Available benches: {', '.join(bench_names) if bench_names else 'none'}",
		)
		return

	domain = "m.frappe.cloud"
	subdomain = name
	full_site = f"{subdomain}.{domain}"

	available_plans = _get_available_plans(session)
	if plan not in available_plans:
		Print.error(console, f"Invalid plan: '{plan}'. Available plans: {', '.join(available_plans)}")
		return

	payload = {
		"apps": apps or [],
		"domain": domain,
		"group": bench,
		"localisation_country": None,
		"name": subdomain,
		"plan": plan,
		"selected_app_plans": {},
		"share_details_consent": False,
	}

	try:
		result = session.post(
			"press.api.site.new",
			json={"site": payload},
			message=f"[bold green]Provisioning site '{full_site}' on bench '{bench}'…",
		)
		if _is_success_response(result):
			installed_list = ", ".join(apps) if apps else "none"
			Print.success(
				console, f"Site '{full_site}' provisioned successfully with apps: {installed_list}."
			)
			return
		if isinstance(result, dict) and result.get("exc_type") == "DuplicateEntryError":
			Print.error(console, f"Duplicate entry: Site '{full_site}' already exists.")
			return
		Print.error(console, f"Failed to provision site: {_format_error_message(result)}")
	except Exception as e:
		resp_text = getattr(getattr(e, "response", None), "text", None)
		if resp_text and "DuplicateEntryError" in resp_text:
			Print.error(console, f"Duplicate entry: Site '{full_site}' already exists.")
			return
		Print.error(console, f"Error provisioning site: {e}")


def _is_success_response(result: object) -> bool:
	if isinstance(result, str):
		return bool(result)
	if isinstance(result, dict):
		return bool(result.get("success") or not result.get("exc_type"))
	return False


def _format_error_message(result: object) -> str:
	if isinstance(result, dict):
		return str(result.get("message") or result.get("exception") or result) or "Unknown error"
	return str(result) or "Unknown error"


def _get_available_plans(session: "CloudSession") -> list[str]:
	resp = session.post("press.api.site.get_site_plans", json={}) or []
	items = resp if isinstance(resp, list) else (resp.get("message", []) if isinstance(resp, dict) else [])
	return [p.get("name") for p in items if isinstance(p, dict) and p.get("name")]


@sites.command(help="Archive (drop) a site")
def drop(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Site name/subdomain (without domain)")],
	force: Annotated[
		bool,
		typer.Option("--force", "-f", is_flag=True, help="Skip confirmation"),
	] = False,
):
	session: CloudSession = ctx.obj
	domain = "m.frappe.cloud"
	full_site = f"{name}.{domain}"

	if (not force) and (
		not typer.confirm(f"Archive site '{full_site}'? This action may be irreversible.", default=False)
	):
		Print.info(console, "Operation cancelled.")
		return

	payload = {
		"dt": "Site",
		"dn": full_site,
		"method": "archive",
		"args": {"force": None},
	}

	try:
		result = session.post(
			"press.api.client.run_doc_method",
			json=payload,
			message=f"[bold red]Archiving site '{full_site}'…",
		)

		if _is_success_response(result):
			Print.success(console, f"Site '{full_site}' archived successfully.")
		else:
			Print.error(console, f"Failed to archive site: {_format_error_message(result)}")
			console.print(result)

	except Exception as e:
		Print.error(console, f"Error archiving site: {e}")
		try:
			resp_text = getattr(getattr(e, "response", None), "text", None)
			if resp_text:
				console.print(resp_text)
		except Exception:
			pass


@sites.command(help="Install app(s) available for a site")
def install_available_apps(
	ctx: typer.Context,
	site: Annotated[str, typer.Argument(help="Full site domain, e.g. foo.m.frappe.cloud")],
	app: Annotated[list[str] | None, typer.Option("--app", help="App(s) to install; omit for all")] = None,
):
	session: CloudSession = ctx.obj

	try:
		resp = session.get("press.api.site.available_apps", params={"name": site}) or []
		available = [x.get("app") for x in (resp if isinstance(resp, list) else []) if x.get("app")]
		if not available:
			return Print.info(console, f"No available apps for '{site}'.")

		target = [a for a in (app or available) if a in available]
		if not target:
			return Print.info(console, "Nothing to install.")

		for name in target:
			result = session.post(
				"press.api.client.run_doc_method",
				json={"dt": "Site", "dn": site, "method": "install_app", "args": {"app": name}},
			)
			if _is_success_response(result):
				Print.success(console, f"Installed '{name}'")
			else:
				Print.error(console, f"Failed '{name}': {_format_error_message(result)}")
	except Exception as e:
		Print.error(console, f"Error: {e}")


@sites.command(help="Uninstall an app from a site")
def uninstall_app(
	ctx: typer.Context,
	site: Annotated[str, typer.Argument(help="Full site domain, e.g. foo.m.frappe.cloud")],
	app: Annotated[str, typer.Option("--app", help="App to uninstall")],
):
	session: CloudSession = ctx.obj

	try:
		result = session.post(
			"press.api.client.run_doc_method",
			json={
				"dt": "Site",
				"dn": site,
				"method": "uninstall_app",
				"args": {"app": app},
			},
			message=f"[bold red]Uninstalling app '{app}' from '{site}'…",
		)
		if _is_success_response(result):
			Print.success(console, f"Uninstalled '{app}' from '{site}'.")
		else:
			Print.error(console, f"Failed to uninstall '{app}': {_format_error_message(result)}")
	except Exception as e:
		Print.error(console, f"Error uninstalling app: {e}")
