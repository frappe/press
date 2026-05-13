import json
import os

import typer
from rich.console import Console

from fc.authentication.login import OtpLogin, session_file_path
from fc.authentication.session import CloudSession

auth = typer.Typer(help="Authentication Commands")
console = Console()


@auth.command(help="Login")
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


@auth.command(help="Logout")
def logout():
	"""Remove stored session info"""
	if os.path.exists(session_file_path):
		os.remove(session_file_path)
	typer.secho("Logged Out", fg="green")


@auth.callback()
def requires_login(ctx: typer.Context):
	if ctx.invoked_subcommand == "login" or ctx.invoked_subcommand == "logout":
		return
	with open(session_file_path, "r") as f:
		session_data = json.load(f)
	session = CloudSession(session_id=session_data["sid"])
	ctx.obj = session
