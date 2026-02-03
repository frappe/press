from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from io import BufferedReader, BytesIO
from typing import TypedDict

import boto3
import botocore.exceptions
import requests
import tomli
from bench.cli import change_working_directory


def _write_assets(file: os.DirEntry, assets_file: str, relative_path: str):
	if os.path.exists(assets_file):
		with open(assets_file, "r+") as f:
			data = json.load(f)
			key_parts = file.name.rsplit(".", maxsplit=2)
			if len(key_parts) > 2:
				key_parts.pop(-2)  # Remove hash part
			key = ".".join(key_parts)

			if key not in data:
				data[key] = relative_path

			f.seek(0)
			json.dump(data, f, indent=4)
			f.truncate()
	else:
		with open(assets_file, "w") as f:
			json.dump({file.name: relative_path}, f, indent=4)


def _write_js_and_css_assets(app: str, dist_folder: str) -> None:
	assets_file = os.path.join(os.getcwd(), "sites", "assets", "assets.json")
	assets_rtl_file = os.path.join(os.getcwd(), "sites", "assets", "assets-rtl.json")

	for assets in ["js", "css"]:
		assets_path = os.path.join(dist_folder, assets)

		if not os.path.exists(assets_path):
			continue

		for file in os.scandir(assets_path):
			if file.name.endswith(".map"):
				continue

			relative_path = f"/assets/{app}/dist/{assets}/{file.name}"
			_write_assets(file, assets_file, relative_path)

	css_rtl_path = os.path.join(dist_folder, "css-rtl")
	if not os.path.exists(css_rtl_path):
		return

	for file in os.scandir(css_rtl_path):
		if file.name.endswith(".map"):
			continue

		relative_path = f"/assets/{app}/dist/css-rtl/{file.name}"
		_write_assets(file, assets_rtl_file, relative_path)


def _update_assets_json(app: str) -> None:
	"""Update assets.json to include the current app's assets."""

	base_assets_path = os.path.join(os.getcwd(), "sites", "assets")
	dist_folder = os.path.join(base_assets_path, app, "dist")

	if not os.path.exists(dist_folder):
		# We don't need to update assets.json if dist folder doesn't exist
		return

	_write_js_and_css_assets(app, dist_folder)


class AssetStoreCredentials(TypedDict):
	secret_access_key: str
	access_key: str
	region_name: str
	endpoint_url: str
	bucket_name: str


@dataclass
class Builder:
	app_name: str
	app_hash: str
	build_token: str
	site_url: str
	upload_assets: bool
	bench_directory: str
	environ: dict[str, str]
	app_path: str
	asset_folder_path: str = ""
	compressed_file_name: str = ""
	app_public_path: str = ""

	@classmethod
	def from_argv(cls, argv: list[str]) -> Builder:
		"""Initialize builder"""
		change_working_directory()
		os.environ["FRAPPE_DOCKER_BUILD"] = "True"

		try:
			return cls(
				app_name=argv[1],
				app_hash=argv[2],
				build_token=argv[3],
				site_url=argv[4],
				upload_assets=bool(int(argv[5])) if len(argv) > 5 else False,
				bench_directory=os.getcwd(),
				environ=os.environ.copy(),
				app_path=f"file:///home/frappe/context/apps/{argv[1]}",
			)
		except (IndexError, ValueError) as e:
			raise ValueError(f"Error parsing arguments: {e}") from e

	def __post_init__(self):
		self.asset_folder_path = os.path.join(self.bench_directory, "sites", "assets", self.app_name)
		self.compressed_file_name = f"{self.app_name}.{self.app_hash}.tar.gz"
		self.app_public_path = os.path.join(
			self.bench_directory, "apps", self.app_name, self.app_name, "public"
		)
		self.pyproject_path = os.path.join(
			self.bench_directory,
			"apps",
			self.app_name,
			"pyproject.toml",
		)

	def tar_and_compress_folder(self):
		"""Tars and compresses the given folder into a .tar.gz file."""
		with tarfile.open(self.compressed_file_name, "w:gz", dereference=True) as tar:
			tar.add(
				self.asset_folder_path,
				arcname=os.path.basename(self.asset_folder_path),
				recursive=True,
			)

	def fallback_bench_build(
		self, credentials: AssetStoreCredentials | None = None, reason: str | None = None
	):
		"""Incase something goes wrong fallback and run bench build"""
		print(
			f"Falling back to bench build due to: {reason if reason else 'unknown reason'} {self.upload_assets=}"
		)
		subprocess.run(
			["bench", "build", "--app", self.app_name, "--production"],
			check=True,
		)

		print(f"Bench build completed for app {self.app_name}.")

		if not credentials or not os.path.exists(self.asset_folder_path) or not self.upload_assets:
			return

		print(f"Uploading assets for app {self.app_name} to store...")
		self.tar_and_compress_folder()
		with open(self.compressed_file_name, "rb") as f:
			self.upload_assets_to_store(
				credentials=credentials,
				file_obj=f,
				file_name=self.compressed_file_name,
			)

		print(f"Assets uploaded for app {self.app_name} to store...")
		os.remove(self.compressed_file_name)

		sys.exit(0)

	def get_asset_store_credentials(self) -> AssetStoreCredentials | None:
		"""Return asset store credentials from remote api to not make it part of the docker image"""
		return (
			requests.get(
				f"{self.site_url}/api/method/press.api.assets.get_credentials",
				headers={
					"build-token": self.build_token,
				},
			)
			.json()
			.get("message")
		)

	def upload_assets_to_store(
		self, credentials: AssetStoreCredentials, file_obj: BufferedReader, file_name: str
	) -> None:
		"""Upload asset stream to store"""
		client = boto3.client(
			"s3",
			region_name=credentials["region_name"],
			endpoint_url=credentials["endpoint_url"],
			aws_access_key_id=credentials["access_key"],
			aws_secret_access_key=credentials["secret_access_key"],
		)

		client.upload_fileobj(
			Fileobj=file_obj,
			Bucket=credentials["bucket_name"],
			Key=file_name,
			ExtraArgs={
				"ContentType": "application/x-tar",
			},
		)

	def download_asset_from_store(self, credentials: AssetStoreCredentials) -> BytesIO:
		"""Download asset from store and return it as a BytesIO stream."""
		client = boto3.client(
			"s3",
			region_name=credentials["region_name"],
			endpoint_url=credentials["endpoint_url"],
			aws_access_key_id=credentials["access_key"],
			aws_secret_access_key=credentials["secret_access_key"],
		)

		file_stream = BytesIO()

		client.download_fileobj(
			Bucket=credentials["bucket_name"],
			Key=self.compressed_file_name,
			Fileobj=file_stream,
		)

		file_stream.seek(0)
		return file_stream

	def has_assets_in_store(self, credentials: AssetStoreCredentials) -> bool:
		"""Check if asset with this commit hash already exists in S3"""
		client = boto3.client(
			"s3",
			region_name=credentials["region_name"],
			endpoint_url=credentials["endpoint_url"],
			aws_access_key_id=credentials["access_key"],
			aws_secret_access_key=credentials["secret_access_key"],
		)

		try:
			client.head_object(
				Bucket=credentials["bucket_name"], Key=f"{self.app_name}.{self.app_hash}.tar.gz"
			)
			return True
		except botocore.exceptions.ClientError:
			return False

	def get_app(self):
		"""Get app without assets"""
		print(f"Fetching app {self.app_name} without assets...")

		subprocess.run(
			["bench", "get-app", self.app_path, "--skip-assets"],
			check=True,
			env=self.environ,
		)

		print(f"App {self.app_name} fetched without assets.")

	def extract_and_link_assets(self, file_stream: BytesIO):
		"""Extracts assets to sites/assets, moves them to the app source, and restores the symlink."""
		# 1. Remove existing symlink/dir so tar can extract a fresh physical directory
		if os.path.exists(self.asset_folder_path):
			if os.path.islink(self.asset_folder_path):
				os.unlink(self.asset_folder_path)
			else:
				shutil.rmtree(self.asset_folder_path)

		# 2. Extract into sites/assets
		with tarfile.open(fileobj=file_stream, mode="r:*") as tar:
			tar.extractall(
				path=os.path.join(
					self.bench_directory, "sites", "assets"
				),  # Extracting it here `self.asset_folder_path` - app_name
				filter="fully_trusted",
			)

		# 3. Move to app public
		if os.path.exists(self.app_public_path):
			shutil.rmtree(self.app_public_path)

		shutil.move(self.asset_folder_path, self.app_public_path)

		# 4. Restore symlink since we deploy with cp -LR
		os.symlink(self.app_public_path, self.asset_folder_path)

		print(f"Assets moved to {self.app_public_path} and symlink restored at {self.asset_folder_path}")

	def run_post_build_commands(self):
		"""Try and run the app's post build command to the best of our ability"""
		build_dir = None
		out_dir = None
		index_html_path = None

		with open(self.pyproject_path, "rb") as f:
			pyproject_data = tomli.load(f)
			assets_keys = pyproject_data.get("tool", {}).get("bench", {}).get("assets", {})
			if not assets_keys:
				self.fallback_bench_build(reason="No assets configuration found in pyproject.toml")

			build_dir = assets_keys.get("build_dir")
			out_dir = assets_keys.get("out_dir")
			index_html_path = assets_keys.get("index_html_path")

		if not build_dir or not out_dir or not index_html_path:
			self.fallback_bench_build(reason="Incomplete assets configuration in pyproject.toml")

		# Paths need to be relative to app root directory
		app_root_path = os.path.join(self.bench_directory, "apps", self.app_name)
		build_dir_path = os.path.join(app_root_path, build_dir)
		out_dir_path = os.path.join(app_root_path, out_dir)
		index_html_path = os.path.join(app_root_path, index_html_path)

		if not os.path.exists(build_dir_path):
			self.fallback_bench_build(reason=f"Build directory does not exist at {build_dir_path}.")

		if not os.path.exists(out_dir_path):
			self.fallback_bench_build(reason=f"Out directory does not exist at {out_dir_path}.")

		# Assuming all other paths are relative to build_dir
		built_assets_index = os.path.join(out_dir_path, "index.html")
		if not os.path.exists(built_assets_index):
			self.fallback_bench_build(reason=f"Built index.html not found at {built_assets_index}.")

		print(f"Copying built index.html from {built_assets_index} to {index_html_path} ...")
		shutil.copy2(built_assets_index, index_html_path)

	def build(self):
		"""Main build function to get/build assets"""
		# Get app without assets
		self.get_app()

		# Check if pyproject.toml exists to ensure it's a valid app
		# Ideally we would never be in this situation as app would not be listed without pyproject.toml
		# Just in case a app with requirements.txt creeps in.
		if not os.path.exists(self.pyproject_path):
			self.fallback_bench_build(reason="pyproject.toml not found.")

		# Check if we can access the asset store
		credentials = self.get_asset_store_credentials()
		if not credentials:
			self.fallback_bench_build(reason="Could not fetch asset store credentials.")

		assets_in_store = self.has_assets_in_store(credentials)
		if not assets_in_store:
			self.fallback_bench_build(
				credentials=credentials,
				reason="Assets not found in store.",
			)

		print(f"Assets found in store for app {self.app_name}. Downloading and extracting...")
		file_stream = self.download_asset_from_store(credentials)
		self.extract_and_link_assets(file_stream)
		self.run_post_build_commands()
		_update_assets_json(self.app_name)


if __name__ == "__main__":
	builder = Builder.from_argv(["", "crm", "app_hash", "build_token", "site_url", "0"])
	builder.run_post_build_commands()
