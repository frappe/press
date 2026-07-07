import json
from typing import Annotated

import typer

from fc.authentication.login import session_file_path
from fc.authentication.session import CloudSession
from fc.commands.assets import build_and_upload_assets
from fc.commands.auth import auth
from fc.commands.deploy import deploy
from fc.commands.server import server
from fc.commands.sites import sites

app = typer.Typer(help="FC CLI")


@app.callback(invoke_without_command=True)
def init_session(ctx: typer.Context):
	"""Initialize CloudSession from saved session file, if present."""
	try:
		with open(session_file_path, "r") as f:
			data = json.load(f)
		ctx.obj = CloudSession(session_id=data["sid"])  # type: ignore[assignment]
	except Exception:
		# No session available yet; auth commands can create one.
		pass


@app.command(help="Runs bench build for a specific app and uploads assets to frappe cloud")
def build(
	ctx: typer.Context,
	app: Annotated[
		str,
		typer.Option("--app", help="App name to build and upload assets for", prompt_required=True),
	],
):
	"""Wrapper for the build command."""
	build_and_upload_assets(ctx, app)


app.add_typer(server, name="server")
app.add_typer(auth, name="auth")
app.add_typer(deploy, name="deploy")
app.add_typer(sites, name="sites")
