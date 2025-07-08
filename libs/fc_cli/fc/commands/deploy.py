import typing
from typing import Any
from urllib.parse import urljoin

import typer
from InquirerPy import inquirer

from fc.models import ClientGet, ClientList, ClientRunDocMethod

if typing.TYPE_CHECKING:
	from rich.console import Console

	from fc.authentication.session import CloudSession


def show_builds(builds, release_group: str, base_url: str, console: "Console"):
	deploy_link = urljoin(base_url, f"dashboard/groups/{release_group}/deploys")

	for build in builds:
		status_color = "green" if build["status"].lower() == "success" else "red"

		console.print(f"  Name:     [bold][link={deploy_link}/{build['name']}]{build['name']}[/link][/bold]")
		console.print(f"  Created:  {build['creation']}")
		console.print(f"  Status:   [{status_color}]{build['status']}[/{status_color}]")
		console.print(f"  Duration: {build['build_duration'] or 'N/A'}")
		console.print(f"  Owner:    {build['owner']}")
		console.print(f"  Apps:     {', '.join(build['apps'])}\n")


def trigger_deploy(
	release_group: str,
	session: "CloudSession",
	console: "Console",
	is_initial_deploy: bool = False,
	apps: list[dict[str, str]] | None = None,
	sites: list[str] | None = None,
):
	base_url = session.base_url.replace("api/method/", "")
	deploy_link = urljoin(base_url, f"dashboard/groups/{release_group}/deploys/")

	if is_initial_deploy:
		response = session.post(
			"press.api.client.run_doc_method",
			json=ClientRunDocMethod(dt="Release Group", dn=release_group, method="initial_deploy"),
			message=f"[bold green]Starting initial deploy for {release_group}...",
		)
		deploy_link = urljoin(deploy_link, response)
		console.print(f"[link={deploy_link}][green]Deploy[/green][/link] Triggered 🚀")
		return

	if not sites:
		sites = []

	response = session.post(
		"press.api.bench.deploy_and_update",
		json={
			"name": release_group,
			"apps": apps,
			"sites": sites,
			"run_will_fail_check": True,
		},
		message=f"[bold green]Starting deploy for {release_group}...",
	)
	deploy_link = urljoin(deploy_link, response)
	console.print(f"[link={deploy_link}][green]Deploy[/green][/link] Triggered 🚀")


def can_deploy(deploy_info: dict[str, Any] | None):
	if not deploy_info:
		typer.secho("No deployment information found", fg="red")
		raise typer.Exit(1)

	if deploy_info.get("deploy_in_progress"):
		typer.secho("Deploy already in progress", fg="red")
		raise typer.Exit(1)

	if not deploy_info.get("update_available"):
		typer.secho("No update available for this bench group", fg="yellow")
		raise typer.Exit(0)


def get_deploy_information_and_deploy(release_group: str, session: "CloudSession", console: "Console"):
	"""
	Fetch deployment information for a given release group and prompt user to select updates for apps.
	"""

	response = session.post(
		"press.api.client.get",
		json=ClientGet(doctype="Release Group", name=release_group),
		message=f"[bold green]Fetching Updates for {release_group}...",
	)

	deploy_info = response.get("deploy_information")
	can_deploy(deploy_info)

	apps = deploy_info.get("apps", [])
	selected_app_updates = []

	for app in apps:
		if not app.get("update_available"):
			continue

		choices = [
			{
				"name": f"[{release['hash'][:7]}] {release['message'].splitlines()[0]}",
				"value": release["name"],
			}
			for release in app.get("releases", [])
		]
		choices.append({"name": f"Skip {app['name']} update", "value": None})

		current = app.get("current_release")
		next_release = app.get("next_release")
		title = app.get("title")

		if current is None:
			trigger_deploy(release_group, session, console, is_initial_deploy=True)
			return

		selection = inquirer.fuzzy(
			pointer="→",
			message=f"{title} ({current}) → {title} ({next_release})",
			choices=choices,
			instruction="(Type to search, ↑↓ to move, Enter to select)",
		).execute()

		if selection:
			release = next((r for r in app.get("releases") if r["name"] == selection), None)
			if release:
				selected_app_updates.append(
					{
						"app": app.get("name"),
						"source": release["source"],
						"release": release["name"],
						"hash": release["hash"],
					}
				)

	if selected_app_updates:
		trigger_deploy(release_group, session, console, apps=selected_app_updates)


def get_deploys(
	release_group: str,
	session: "CloudSession",
	console: "Console",
	start: int = 0,
	limit: int = 5,
) -> list:
	increment_by = 5
	all_deploys = []

	while True:
		deploy_data = ClientList(
			doctype="Deploy Candidate Build",
			fields=["name", "creation", "status", "build_duration", "owner"],
			filters={"group": release_group},
			start=start,
			limit=limit,
			debug=0,
		)

		response = session.get(
			"press.api.client.get_list",
			json=deploy_data,
			message=f"[bold green]Fetching deploys for {release_group} (offset {start})...",
		)

		if not response:
			console.print("[bold yellow]No more deploys found.[/bold yellow]")
			break

		base_url = session.base_url.replace("api/method/", "")
		show_builds(response, release_group, base_url, console)
		all_deploys.extend(response)

		choice = typer.prompt("Show more? [y/N]").strip().lower()
		if choice != "y":
			break

		start += increment_by

	return all_deploys
