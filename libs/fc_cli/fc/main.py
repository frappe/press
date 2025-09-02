import json
import os

import typer
from rich.console import Console

from fc.authentication.login import OtpLogin, session_file_path
from fc.authentication.session import CloudSession
from fc.commands.deploy import get_deploy_information_and_deploy, get_deploys
from fc.commands.servers import server_usage
from fc.models import ClientList

app = typer.Typer(help="FC CLI")
deploy = typer.Typer(help="Manage deploys")
server = typer.Typer(help="Server Info")

console = Console()


### Authentication Commands
@app.command(help="Login")
def login(email: str):
	"""Log user in using email"""
	login_handler = OtpLogin(email)

	if login_handler.verify_existing_session():
		typer.secho("Logged In", fg="green")
		return

	with console.status(f"[bold green]Sending OTP to {email}...", spinner="dots"):
		login_handler.send_otp()

	typer.secho(f"OTP sent to {email}...", fg="cyan")
	otp = typer.prompt("OTP")

	with console.status("[bold green]Verifying OTP...", spinner="dots"):
		session_metadata = login_handler.verify_otp_and_get_session_metadata(otp)
		session_metadata.save()

	typer.secho("Logged In", fg="green")


@app.command(help="Logout")
def logout():
	"""Remove stored session info"""
	if os.path.exists(session_file_path):
		os.remove(session_file_path)

	typer.secho("Logged Out", fg="green")


@app.callback()
def requires_login(ctx: typer.Context):
	if ctx.invoked_subcommand == "login" or ctx.invoked_subcommand == "logout":
		return

	with open(session_file_path, "r") as f:
		session_data = json.load(f)

	session = CloudSession(session_id=session_data["sid"])
	ctx.obj = session


### Authentication Commands


@server.command(help="List servers")
def usage(ctx: typer.Context, name: str = typer.Option(None, "--name", "-n", help="Server name")):
	session: CloudSession = ctx.obj
	server_data = ClientList(
		doctype="Server",
		fields=[
			"name",
			"title",
			"database_server",
			"plan.title as plan_title",
			"plan.price_usd as price_usd",
			"plan.price_inr as price_inr",
			"cluster.image as cluster_image",
			"cluster.title as cluster_title",
			"name",
			"status",
			"db_plan",
			"cluster",
		],
		filters={},
		order_by="creation desc",
		start=0,
		limit=20,
		limit_start=0,
		limit_page_length=20,
		debug=0,
	)

	response = session.post(
		"press.api.client.get_list", json=server_data, message="[bold green]Getting servers..."
	)

	values = [res["name"] for res in response]
	values += [res["database_server"] for res in response]
	if not values:
		typer.secho("No servers found.", fg="red")
		return

	if not name:
		typer.secho("Please provide a server name using --name.", fg="yellow")
		return

	if name not in values:
		typer.secho(f"Server '{name}' not found.", fg="red")
		return

	server_usage(name, session, console)


def get_release_groups(session: CloudSession) -> list[dict[str, str]]:
	"""Get all release groups in for a user"""
	release_group_data = ClientList(
		doctype="Release Group",
		filters={},
		fields=["name", "title"],
		start=0,
		limit=99999,
		limit_start=0,
		limit_page_length=99999,
		debug=0,
	)
	message = session.post(
		"press.api.client.get_list", json=release_group_data, message="[bold green]Getting bench groups..."
	)
	return [{"name": info["title"], "value": info["name"]} for info in message]


@deploy.command(help="Create a new deploy")
def create_deploy(ctx: typer.Context):
	session: CloudSession = ctx.obj
	release_groups = get_release_groups(session)
	if not release_groups:
		typer.secho("No release groups found.", fg="red")
		return
	choices = [rg["name"] for rg in release_groups]
	values = [rg["value"] for rg in release_groups]
	selected_name = typer.prompt("Select Release Group", type=typer.Choice(choices, case_sensitive=False))
	idx = choices.index(selected_name)
	selection = values[idx]
	get_deploy_information_and_deploy(selection, session, console)


@deploy.command(help="Get deploys of bench group")
def show_deploy(ctx: typer.Context):
	session: CloudSession = ctx.obj
	release_groups = get_release_groups(session)
	if not release_groups:
		typer.secho("No release groups found.", fg="red")
		return
	choices = [rg["name"] for rg in release_groups]
	values = [rg["value"] for rg in release_groups]
	selected_name = typer.prompt("Select Release Group", type=typer.Choice(choices, case_sensitive=False))
	idx = choices.index(selected_name)
	release_group = values[idx]
	get_deploys(release_group, session, console)


@server.command(help="Shows the current plan for a server")
def server_plan(ctx: typer.Context, name: str = typer.Option(..., "--name", "-n", help="Server name")):
	session: CloudSession = ctx.obj
	doctype = None
	if name and name.startswith("f"):
		doctype = "Server"
	elif name and name.startswith("m"):
		doctype = "Database Server"
	else:
		doctype = "Database Server"
	payload = {
		"doctype": doctype,
		"name": name,
		"fields": [
			"current_plan",
		],
		"debug": 0,
	}
	response = session.post(
		"press.api.client.get", json=payload, message="[bold green]Getting database server details..."
	)
	if not response or "current_plan" not in response:
		typer.secho(f"{doctype} '{name}' or its current plan not found.", fg="red")
		return

	plan = response["current_plan"]
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


@server.command(help="Increase storage for a server")
def increase_storage(
	ctx: typer.Context,
	name: str = typer.Option(..., "--name", "-n", help="Server name"),
	increment: int = typer.Option(..., "--increment", "-i", help="Increment size in GB"),
):
	session: CloudSession = ctx.obj
	if name.startswith("f"):
		doctype = "Server"
	else:
		doctype = "Database Server"
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

	console.print(
		f"Storage increased for server [bold blue]{name}[/bold blue] by [bold blue]{increment}[/bold blue] GB",
		style="bold",
	)


app.add_typer(deploy, name="deploy")
app.add_typer(server, name="server")

if __name__ == "__main__":
	app()
