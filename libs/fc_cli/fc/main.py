import json

import typer

from fc.authentication.login import session_file_path
from fc.authentication.session import CloudSession
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


app.add_typer(server, name="server")
app.add_typer(auth, name="auth")
app.add_typer(deploy, name="deploy")
app.add_typer(sites, name="sites")
