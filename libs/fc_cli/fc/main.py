import json
import os

import typer
from InquirerPy import inquirer
from rich.console import Console

from fc.authentication.login import OtpLogin, session_file_path
from fc.authentication.session import CloudSession
from fc.deploy import get_deploy_information
from fc.models import ClientList

app = typer.Typer(help="FC CLI - Deploy Utility!")


console = Console()


### Authentication Command
@app.command()
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


@app.command()
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


@app.command()
def servers(ctx: typer.Context):
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
	selection = inquirer.fuzzy(
		message="Select Release Group",
		choices=[
			{"name": res["title"] if res["title"] else res["name"], "value": res["name"]} for res in response
		],
		pointer="→",
		instruction="(Type to search, ↑↓ to move, Enter to select)",
	).execute()
	print(selection)


@app.command()
def create_deploy(ctx: typer.Context):
	session: CloudSession = ctx.obj
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
	options = [{"name": info["title"], "value": info["name"]} for info in message]

	selection = inquirer.fuzzy(
		message="Select Release Group",
		choices=options,
		pointer="→",
		instruction="(Type to search, ↑↓ to move, Enter to select)",
	).execute()

	get_deploy_information(selection, session, console)


if __name__ == "__main__":
	app()
