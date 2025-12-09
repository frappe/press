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
def new_site(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Site name/subdomain (name)")],
	version: Annotated[str, typer.Option("--version", help="Stack version (version)")],
	cluster: Annotated[str, typer.Option("--cluster", help="Cluster/region (cluster)")],
	plan: Annotated[str, typer.Option("--plan", help="Plan (plan)")],
	apps: Annotated[list[str], typer.Option("--apps", help="Apps list (apps)")],
):
	"""Create a new site on a bench after checking availability.

	Maps args to payload for press.api.site.new:
	- apps -> list[str]
	- cluster -> region
	- domain -> domain
	- group -> bench
	- localisation_country -> None
	- name -> subdomain
	- plan -> plan
	- selected_app_plans -> {}
	- share_details_consent -> False
	- version -> version
	"""
	session: CloudSession = ctx.obj
	bench = _pick_bench_with_apps(session, apps) or _pick_default_bench(session)
	if not bench:
		Print.error(console, "No bench groups found. Please create a bench group first.")
		return

	domain = "m.frappe.cloud"
	subdomain = name
	full_site = f"{subdomain}.{domain}"

	try:
		# Check availability first
		availability = session.post(
			"press.api.site.exists",
			json={"domain": domain, "subdomain": subdomain},
			message="Checking availability…",
		)
		if isinstance(availability, dict) and availability.get("exists"):
			Print.error(console, f"Site name '{full_site}' is not available")
			return

		payload = {
			"apps": apps or [],
			"cluster": cluster,
			"domain": domain,
			"group": bench,
			"localisation_country": None,
			"name": subdomain,
			"plan": plan,
			"selected_app_plans": {},
			"share_details_consent": False,
			"version": version,
		}

		result = session.post(
			"press.api.site.new",
			json={"site": payload},
			message=f"[bold green]Provisioning site '{full_site}' on bench '{bench}'…",
		)

		if _is_success_response(result):
			Print.success(
				console,
				f"Site '{full_site}' provisioned successfully with apps: {', '.join(apps) if apps else 'none'}.",
			)
		else:
			Print.error(console, f"Failed to provision site: {_format_error_message(result)}")
			# Print raw backend response for debugging
			console.print(result)

	except Exception as e:
		Print.error(console, f"Error provisioning site: {e}")
		# Print raw backend response body if available
		try:
			resp_text = getattr(getattr(e, "response", None), "text", None)
			if resp_text:
				console.print(resp_text)
		except Exception:
			pass


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


def _pick_default_bench(session: "CloudSession") -> str | None:
	"""Return the first available bench group name, or None if none exist."""
	benches = session.get("press.api.bench.all") or []
	if isinstance(benches, list) and benches:
		return benches[0].get("name")
	return None


@sites.command(help="Archive (drop) a site")
def drop_site(
	ctx: typer.Context,
	name: Annotated[str, typer.Argument(help="Site name/subdomain (without domain)")],
	force: Annotated[
		bool,
		typer.Option("--force", "-f", is_flag=True, help="Skip confirmation"),
	] = False,
):
	"""Archive a site via press.api.client.run_doc_method using the provided payload shape."""
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


def _pick_bench_with_apps(session: "CloudSession", apps: list[str]) -> str | None:
	"""Return the name of a bench that contains all requested apps, if any."""
	try:
		benches = session.get("press.api.bench.all") or []
		for bench in benches or []:
			bench_name = bench.get("name")
			bench_apps = {a.get("app") for a in (bench.get("apps") or []) if a.get("app")}
			if apps and set(apps).issubset(bench_apps):
				return bench_name
	except Exception:
		return None
	return None
