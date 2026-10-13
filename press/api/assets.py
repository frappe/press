from __future__ import annotations

from typing import TYPE_CHECKING, Any, BinaryIO

import boto3
import botocore.exceptions
import frappe

if TYPE_CHECKING:
	from press.press.doctype.press_settings.press_settings import PressSettings

SIGNED_URL_EXPIRY = 15 * 60


def _get_asset_store() -> tuple[Any, str]:
	"""Return an S3 client for the asset store and its bucket name."""
	settings: PressSettings = frappe.get_cached_doc("Press Settings")
	client = boto3.client(
		"s3",
		region_name=settings.asset_store_region,
		endpoint_url=settings.asset_store_endpoint,
		aws_access_key_id=settings.asset_store_access_key,
		aws_secret_access_key=settings.get_password("asset_store_secret_access_key"),
	)
	return client, settings.asset_store_bucket_name


def asset_exists(client: Any, bucket: str, file_name: str) -> bool:
	try:
		client.head_object(Bucket=bucket, Key=file_name)
		return True
	except botocore.exceptions.ClientError:
		return False


def sign_url(client: Any, method: str, bucket: str, file_name: str) -> str:
	return client.generate_presigned_url(
		method, Params={"Bucket": bucket, "Key": file_name}, ExpiresIn=SIGNED_URL_EXPIRY
	)


def get_running_build_group(build_token: str | None) -> tuple[str, str]:
	"""Return the deploy candidate and release group of the running build this token belongs to."""
	if not build_token:
		frappe.throw("Build token is required to access the asset store", frappe.PermissionError)

	candidate = frappe.db.get_value("Deploy Candidate", {"build_token": build_token}, ["name", "group"])
	if not candidate:
		frappe.throw("Invalid build token used", frappe.PermissionError)

	if not frappe.db.exists(
		"Deploy Candidate Build", {"deploy_candidate": candidate[0], "status": "Running"}
	):
		frappe.throw("Expired token used", frappe.PermissionError)

	return candidate[0], candidate[1]


@frappe.whitelist(allow_guest=True)
def get_asset_urls(app: str, hash: str) -> dict[str, str]:
	"""Sign a download URL if the app's assets are stored, else an upload URL.

	Builds get URLs for their own apps only, never the store's keys.
	"""
	candidate, group = get_running_build_group(frappe.request.headers.get("build-token"))

	if not frappe.db.get_value("Release Group", group, "public"):
		frappe.throw("Asset store is only available to public bench groups", frappe.PermissionError)

	if not frappe.db.exists("Deploy Candidate App", {"parent": candidate, "app": app, "hash": hash}):
		frappe.throw(f"App {app} at {hash} is not part of this build", frappe.PermissionError)

	client, bucket = _get_asset_store()
	file_name = f"{app}.{hash}.tar.gz"
	if asset_exists(client, bucket, file_name):
		return {"download_url": sign_url(client, "get_object", bucket, file_name)}

	return {"upload_url": sign_url(client, "put_object", bucket, file_name)}


def upload_assets_to_store(client: Any, bucket: str, file_obj: BinaryIO, file_name: str) -> None:
	client.upload_fileobj(
		Fileobj=file_obj,
		Bucket=bucket,
		Key=file_name,
		ExtraArgs={"ContentType": "application/x-tar"},
	)


@frappe.whitelist()
def upload_asset():
	# Builds trust stored assets for every public bench, so only staff may upload
	frappe.only_for("System Manager")

	files = frappe.request.files
	if not files or "asset_file" not in files:
		frappe.throw("No file was uploaded. Please attach an asset file and try again.")

	asset_file = files["asset_file"]
	client, bucket = _get_asset_store()
	if asset_exists(client, bucket, asset_file.filename):
		frappe.throw(f"Asset with name {asset_file.filename} already exists in the asset store")

	upload_assets_to_store(client, bucket, asset_file.stream, asset_file.filename)
