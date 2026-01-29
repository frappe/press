from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
from io import BytesIO
from typing import TypedDict

import boto3
import botocore.exceptions
import requests
from bench.cli import change_working_directory

APP_NAME = sys.argv[1]
APP_HASH = sys.argv[2]
BUILD_TOKEN = sys.argv[3]
SITE_URL = sys.argv[4]
try:
	UPLOAD_ASSETS = bool(int(sys.argv[5]))
except Exception as e:
	print(f"Could not parse upload assets flag: {e}")
	UPLOAD_ASSETS = False


class AssetStoreCredentials(TypedDict):
	secret_access_key: str
	access_key: str
	region_name: str
	endpoint_url: str
	bucket_name: str


def get_asset_store_credentials() -> AssetStoreCredentials:
	"""Return asset store credentials from remote api to not make it part of the docker image"""
	return requests.get(
		f"{SITE_URL}/api/method/press.api.assets.get_credentials",
		headers={"build-token": BUILD_TOKEN},
	).json()["message"]


def check_existing_asset_in_s3(credentials: AssetStoreCredentials, file_name: str) -> bool:
	"""Check if asset with this commit hash already exists in S3"""
	client = boto3.client(
		"s3",
		region_name=credentials["region_name"],
		endpoint_url=credentials["endpoint_url"],
		aws_access_key_id=credentials["access_key"],
		aws_secret_access_key=credentials["secret_access_key"],
	)

	try:
		client.head_object(Bucket=credentials["bucket_name"], Key=file_name)
		return True
	except botocore.exceptions.ClientError:
		return False


def upload_assets_to_store(credentials: AssetStoreCredentials, file_obj: BytesIO, file_name: str) -> None:
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


def download_asset_from_store(credentials: AssetStoreCredentials, file_name: str) -> BytesIO:
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
		Key=file_name,
		Fileobj=file_stream,
	)

	file_stream.seek(0)
	return file_stream


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
	change_working_directory()

	base_assets_path = os.path.join(os.getcwd(), "sites", "assets")
	dist_folder = os.path.join(base_assets_path, app, "dist")

	if not os.path.exists(dist_folder):
		# We don't need to update assets.json if dist folder doesn't exist
		return

	_write_js_and_css_assets(app, dist_folder)


def tar_and_compress_folder(folder_path: str, output_filename: str) -> str:
	"""Tars and compresses the given folder into a .tar.gz file."""
	with tarfile.open(output_filename, "w:gz", dereference=True) as tar:
		tar.add(folder_path, arcname=os.path.basename(folder_path), recursive=True)
	return output_filename


def build_assets(app: str) -> str:
	"""Build assets for the app using the app name and return the path to assets"""
	change_working_directory()
	env = os.environ.copy()
	env["FRAPPE_DOCKER_BUILD"] = "True"
	completed_process = subprocess.run(
		["bench", "build", "--app", app, "--production"],
		check=True,
		env=env,
	)
	assets_path = os.path.join(os.getcwd(), "sites", "assets", app)
	print(f"Build Command Completed. Return Code: {completed_process.returncode}.")
	return assets_path


def extract_and_link_assets(app_name: str, file_stream: BytesIO):
	"""
	Extracts assets to sites/assets, moves them to the app source, and restores the symlink.
	"""
	change_working_directory()
	bench_path = os.getcwd()

	app_public_path = os.path.join(bench_path, "apps", app_name, app_name, "public")
	assets_path = os.path.join(bench_path, "sites", "assets", app_name)

	# 1. Remove existing symlink/dir so tar can extract a fresh physical directory
	if os.path.exists(assets_path):
		if os.path.islink(assets_path):
			os.unlink(assets_path)
		else:
			shutil.rmtree(assets_path)

	# 2. Extract into sites/assets
	with tarfile.open(fileobj=file_stream, mode="r:*") as tar:
		tar.extractall(path=os.path.join(bench_path, "sites", "assets"), filter="fully_trusted")

	# 3. Move to app public
	if os.path.exists(app_public_path):
		shutil.rmtree(app_public_path)

	shutil.move(assets_path, app_public_path)

	# 4. Restore symlink since we deploy with cp -LR
	os.symlink(app_public_path, assets_path)

	print(f"Assets moved to {app_public_path} and symlink restored at {assets_path}")


def main():
	"""Get cached app assets or build and upload them"""
	if not APP_NAME or not APP_HASH:
		return

	credentials = get_asset_store_credentials()
	asset_filename = f"{APP_NAME}.{APP_HASH}.tar.gz"

	env = os.environ.copy()
	env["FRAPPE_DOCKER_BUILD"] = "True"
	app_path = f"file:///home/frappe/context/apps/{APP_NAME}"

	print("Fetching app without assets...")
	subprocess.run(["bench", "get-app", app_path, "--skip-assets"], check=True, env=env)

	if check_existing_asset_in_s3(credentials, asset_filename):
		print(f"Assets {asset_filename} found in store. Extracting and setting up...")
		file_stream = download_asset_from_store(credentials, asset_filename)
		extract_and_link_assets(APP_NAME, file_stream)
		_update_assets_json(APP_NAME)
	else:
		print(f"Assets {asset_filename} not found in store. Building...")
		assets_folder = build_assets(APP_NAME)
		if not os.path.exists(assets_folder) or not os.path.isdir(assets_folder):
			print(f"No assets found for app {APP_NAME} at {assets_folder}.")
			return

		if UPLOAD_ASSETS:
			print("Upload requested. Uploading assets to store...")
			tar_file = tar_and_compress_folder(assets_folder, asset_filename)

			with open(tar_file, "rb") as f:
				upload_assets_to_store(credentials, f, asset_filename)

			os.remove(tar_file)


if __name__ == "__main__":
	main()
