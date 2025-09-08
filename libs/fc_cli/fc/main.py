import json
import os

import typer
from rich.console import Console

from fc.authentication.login import OtpLogin, session_file_path
from fc.authentication.session import CloudSession
from fc.commands.servers import server_usage
from fc.models import ClientList

app = typer.Typer(help="FC CLI")
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

	try:
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

		if not response:
			typer.secho("Failed to retrieve servers.", fg="red")
			return

	except Exception as e:
		typer.secho(f"Error fetching servers: {e!s}", fg="red")
		return

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

	try:
		server_usage(name, session, console)
	except Exception as e:
		typer.secho(f"Error getting server usage: {e!s}", fg="red")


@server.command(help="Shows the current plan for a server")
def server_plan(ctx: typer.Context, name: str = typer.Option(..., "--name", "-n", help="Server name")):
	session: CloudSession = ctx.obj

	try:
		doctype = None
		if name and name.startswith("f"):
			doctype = "Server"

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

	except Exception as e:
		typer.secho(f"Error getting server plan: {e!s}", fg="red")


@server.command(help="Increase storage for a server")
def increase_storage(
	ctx: typer.Context,
	name: str = typer.Option(..., "--name", "-n", help="Server name"),
	increment: int = typer.Option(..., "--increment", "-i", help="Increment size in GB"),
):
	session: CloudSession = ctx.obj
	if not name.endswith("frappe.cloud"):
		typer.secho(f"Invalid server name: '{name}'. Server name must end with 'frappe.cloud'", fg="red")
		return

	try:
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

		if response and response.get("success") is False:
			typer.secho(f"Failed to increase storage: {response.get('message', 'Unknown error')}", fg="red")
			return

		console.print(
			f"Storage increased for server [bold blue]{name}[/bold blue] by [bold blue]{increment}[/bold blue] GB",
			style="bold",
		)

	except Exception as e:
		typer.secho(f"Error increasing storage: {e!s}", fg="red")


@server.command(help="Show details about a specific plan for a server")
def show_plan(
	ctx: typer.Context,
	name: str = typer.Option(..., "--name", "-n", help="Server name"),
	plan: str = typer.Option(..., "--plan", "-p", help="Plan name"),
):
	session: CloudSession = ctx.obj

	try:
		doctype = "Server" if name.startswith("f") else "Database Server"
		payload = {"name": doctype, "cluster": "Mumbai", "platform": "arm64"}

		plans = session.post(
			"press.api.server.plans", json=payload, message="[bold green]Fetching available server plans..."
		)

		selected_plan = next((p for p in plans if p.get("name") == plan), None)
		if not selected_plan:
			typer.secho(f"Plan '{plan}' not found for server '{name}'", fg="red")
			return

		console.print("[bold]Plan Details:[/bold]")
		console.print(f"[bold]Name:[/bold] [bold]{selected_plan.get('name', '-')}")
		console.print(f"[bold]Price:[/bold] [bold]₹{selected_plan.get('price_inr', '-')} /mo")
		console.print(
			f"[bold]vCPUs:[/bold] [bold]{selected_plan.get('vcpu', '-')}\n[bold]Memory:[/bold] [bold]{selected_plan.get('memory', '-')} GB\n[bold]Disk:[/bold] [bold]{selected_plan.get('disk', '-')} GB"
		)

	except Exception as e:
		typer.secho(f"Error fetching plan details: {e!s}", fg="red")


@server.command(help="Show current plan and choose available server plans")
def choose_plan(
	ctx: typer.Context,
	name: str = typer.Option(..., "--name", "-n", help="Name of the server"),
	plan: str = typer.Option(..., "--plan", "-o", help="Name of the plan"),
):
	session: CloudSession = ctx.obj

	try:
		doctype = "Server" if name.startswith("f") else "Database Server"

		payload = {"name": doctype, "cluster": "Mumbai", "platform": "arm64"}
		plans = session.post(
			"press.api.server.plans", json=payload, message="[bold green]Fetching available server plans..."
		)

		selected_plan = next((p for p in plans if p.get("name") == plan), None)
		if not selected_plan:
			typer.secho(f"Plan '{plan}' not found for server '{name}'", fg="red")
			return

		change_payload = {
			"dt": doctype,
			"dn": name,
			"method": "change_plan",
			"args": {"plan": selected_plan.get("name")},
		}

		response = session.post(
			"press.api.client.run_doc_method",
			json=change_payload,
			message=f"[bold green]Changing plan for {name} to {selected_plan.get('name')}...",
		)

		if response and response.get("success") is False:
			typer.secho(f"Failed to change plan: {response.get('message', 'Unknown error')}", fg="red")
			return

		console.print("[bold]Successfully changed plan![/bold]")
		console.print("[bold]Plan Details:[/bold]")
		console.print(f"[bold]Name:[/bold] [bold]{selected_plan.get('name', '-')}")
		console.print(f"[bold]Price:[/bold] [bold]₹{selected_plan.get('price_inr', '-')} /mo")
		console.print(f"[bold]vCPUs:[/bold] [bold]{selected_plan.get('vcpu', '-')}")
		console.print(f"[bold]Memory:[/bold] [bold]{selected_plan.get('memory', '-')} GB")
		console.print(f"[bold]Disk:[/bold] [bold]{selected_plan.get('disk', '-')} GB")

	except Exception as e:
		typer.secho(f"Error changing plan: {e!s}", fg="red")


@server.command(help="Create a new server")
def create_server(
	ctx: typer.Context,
	cluster: str = typer.Option(..., "--cluster", help="Cluster name"),
	title: str = typer.Option(..., "--title", help="Server title"),
	app_plan: str = typer.Option(..., "--app-plan", help="App server plan name"),
	db_plan: str = typer.Option(..., "--db-plan", help="Database server plan name"),
	auto_increase_storage: bool = typer.Option(
		False, "--auto-increase-storage", is_flag=True, help="Auto increase storage"
	),
):
	session: CloudSession = ctx.obj

	try:
		server_payload = {
			"cluster": cluster,
			"title": title,
			"app_plan": app_plan,
			"db_plan": db_plan,
			"auto_increase_storage": auto_increase_storage,
		}

		response = session.post(
			"press.api.server.new",
			json={"server": server_payload},
			message=f"[bold green]Creating server '{title}' in cluster '{cluster}'...",
		)

		if not response or not response.get("server"):
			typer.secho(
				f"Failed to create server: {response.get('message', 'Unknown error') if response else 'No response from backend.'}",
				fg="red",
			)
			return

		typer.secho(f"Successfully created server: {response['server']}", fg="green")
		if response.get("job"):
			typer.secho(f"Job started: {response['job']}", fg="cyan")

	except Exception as e:
		typer.secho(f"Error creating server: {e!s}", fg="red")


@server.command(help="Delete a server (archive)")
def delete_server(
	ctx: typer.Context,
	name: str = typer.Option(..., "--name", help="Name of the server to delete"),
):
	session: CloudSession = ctx.obj

	try:
		response = session.post(
			"press.api.server.archive", json={"name": name}, message=f"[bold red]Archiving server '{name}'..."
		)

		if response and response.get("exc_type"):
			typer.secho(f"Failed to delete server: {response.get('exception', 'Unknown error')}", fg="red")
			return

		typer.secho(f"Successfully deleted (archived) server: {name}", fg="green")

	except Exception as e:
		typer.secho(f"Error deleting server: {e!s}", fg="red")


app.add_typer(server, name="server")


if __name__ == "__main__":
	app()
