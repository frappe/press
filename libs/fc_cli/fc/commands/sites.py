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
	bench_opt: Annotated[str, typer.Option("--bench", help="Bench group name (group)")],
	version: Annotated[str, typer.Option("--version", help="Stack version (version)")],
	cluster: Annotated[str, typer.Option("--cluster", help="Cluster/region (cluster)")],
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
	print(available_plans)

	if not _is_valid_plan(session, plan):
		Print.error(console, f"Invalid plan: '{plan}'. Available plans: {', '.join(available_plans)}")
		return

	# Skip backend availability precheck per user request; rely on backend response

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

	try:
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
			return
		exc_type = result.get("exc_type") if isinstance(result, dict) else None
		if exc_type == "DuplicateEntryError":
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


def _pick_default_bench(session: "CloudSession") -> str | None:
	"""Return the first available bench group name, or None if none exist."""
	benches = session.get("press.api.bench.all") or []
	if isinstance(benches, list) and benches:
		return benches[0].get("name")
	return None


def _get_available_plans(session: "CloudSession") -> list[str]:
	resp = session.post("press.api.site.get_site_plans", json={}) or []
	items = resp if isinstance(resp, list) else (resp.get("message", []) if isinstance(resp, dict) else [])
	return [p.get("name") for p in items if isinstance(p, dict) and p.get("name")]


def _is_valid_plan(session: "CloudSession", plan: str) -> bool:
	return plan in _get_available_plans(session)


def _is_site_available(session: "CloudSession", domain: str, subdomain: str) -> bool:
	availability = session.post(
		"press.api.site.exists",
		json={"domain": domain, "subdomain": subdomain},
		message="Checking availability…",
	)
	return not (isinstance(availability, dict) and availability.get("exists"))


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
