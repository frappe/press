from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, TypedDict

import boto3
import botocore.exceptions
import frappe

if TYPE_CHECKING:
	from apps.press.press.press.doctype.press_settings.press_settings import PressSettings


class AssetStoreCredentials(TypedDict):
	secret_access_key: str
	access_key: str
	region_name: str
	endpoint_url: str
	bucket_name: str


def _get_asset_store_credentials() -> AssetStoreCredentials:
	"""Return asset store credentials from Press Settings."""
	settings: PressSettings = frappe.get_cached_doc("Press Settings")

	return {
		"secret_access_key": settings.get_password("asset_store_secret_access_key"),
		"access_key": settings.asset_store_access_key,
		"region_name": settings.asset_store_region,
		"endpoint_url": settings.asset_store_endpoint,
		"bucket_name": settings.asset_store_bucket_name,
	}


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


@frappe.whitelist()
def upload_asset():
	files = frappe.request.files

	if not files or "asset_file" not in files:
		frappe.throw("No asset file uploaded")

	asset_file = files["asset_file"]
	credentials = _get_asset_store_credentials()

	has_existing_asset = check_existing_asset_in_s3(credentials, asset_file.filename)
	if has_existing_asset:
		frappe.throw(f"Asset with name {asset_file.filename} already exists in the asset store")

	upload_assets_to_store(credentials, asset_file.stream, asset_file.filename)


@frappe.whitelist(allow_guest=True)
def get_credentials() -> AssetStoreCredentials:
	"""Get asset store credentials if it is requested from a build server"""
	build_token = frappe.request.headers.get("build-token")
	if not build_token:
		frappe.throw("Build token is required to access asset store credentials", frappe.PermissionError)

	deploy_candidate = frappe.db.get_value("Deploy Candidate", {"build_token": build_token})
	if not deploy_candidate:
		frappe.throw("Invalid build token used", frappe.PermissionError)

	running_build = frappe.db.get_value(
		"Deploy Candidate Build", {"deploy_candidate": deploy_candidate, "status": "Running"}
	)

	if not running_build:
		frappe.throw("Expired token used", frappe.PermissionError)

	return _get_asset_store_credentials()
