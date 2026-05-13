from __future__ import annotations

import os
import subprocess
import tarfile
from typing import TYPE_CHECKING, Annotated

import typer
from bench.cli import change_working_directory
from bench.utils import is_bench_directory
from requests.exceptions import HTTPError
from rich.console import Console

from fc.commands.deploy import _build_method_url
from fc.printer import Print

if TYPE_CHECKING:
	from fc.authentication.session import CloudSession

console = Console()
assets_path = None


def tar_and_compress_folder(folder_path: str, output_filename: str) -> str:
	"""Tars and compresses the given folder into a .tar.gz file."""
	with tarfile.open(output_filename, "w:gz") as tar:
		tar.add(folder_path, arcname=os.path.basename(folder_path))
	return output_filename


def get_app_commit_info(app: str) -> str:
	"""Gets the current git commit hash for the specified app."""
	app_path = os.path.join(os.getcwd(), "apps", app)
	if not os.path.exists(app_path):
		Print.error(
			console=console,
			message=f"App does not exist at expected path: {app_path}",
		)
		raise typer.Exit(code=1)

	try:
		return (
			subprocess.check_output(
				["git", "-C", app_path, "rev-parse", "HEAD"],
				stderr=subprocess.DEVNULL,
			)
			.decode("utf-8")
			.strip()
		)
	except subprocess.CalledProcessError:
		Print.error(
			console=console,
			message=f"Failed to get commit hash for app '{app}'. Is it a git repository?",
		)
		raise typer.Exit(code=1) from None


def build_and_upload_assets(
	ctx: typer.Context,
	app: Annotated[
		str,
		typer.Option("--app", "-a", help="App name to build and upload assets for", prompt_required=True),
	],
):
	"""Builds the specified app and uploads its assets to Frappe Cloud."""
	session: CloudSession = ctx.obj

	if not session:
		Print.error(
			console=console,
			message="You must be logged in to use this command. Please run 'press-cli auth login' first.",
		)
		raise typer.Exit(code=1)

	change_working_directory()  # We move into the parent bench directory
	is_bench_dir = is_bench_directory()

	if not is_bench_dir:
		Print.error(
			console=console,
			message="This command must be run inside a Bench directory.",
		)
		raise typer.Exit(code=1)

	Print.code(console=console, message=f"$ bench build --app {app}")
	subprocess.run(["bench", "build", "--app", app], check=True)
	Print.info(console=console, message=f"Uploading assets for app '{app}' to Frappe Cloud...")

	# Since we moved into the bench directory we can get the current directory and build the path to the assets
	assets_folder = os.path.join(os.getcwd(), "sites", "assets", app)
	commit = get_app_commit_info(app)
	tar_file = tar_and_compress_folder(assets_folder, f"{app}.{commit}.tar.gz")

	if not os.path.exists(assets_folder):
		Print.error(
			console=console,
			message=f"Assets folder for app '{app}' does not exist at expected path: {assets_folder} something went wrong!",
		)
		raise typer.Exit(code=1)

	url = _build_method_url(session, "press.api.assets.upload_asset")

	try:
		with open(tar_file, "rb") as f:
			session.post(
				url,
				files={
					"asset_file": (
						os.path.basename(tar_file),
						f,
						"application/gzip",
					)
				},
			)

	except HTTPError as e:
		Print.error(
			console=console,
			message=f"Failed to upload assets for app '{app}': {e}",
		)
		raise typer.Exit(code=1) from None
	finally:
		os.remove(tar_file)

	Print.success(
		console=console,
		message=f"Assets for app '{app}' uploaded successfully!",
	)
