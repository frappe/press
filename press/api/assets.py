from __future__ import annotations

from typing import TYPE_CHECKING, Any, BinaryIO

import boto3
import botocore.exceptions
import frappe

if TYPE_CHECKING:
	from press.press.doctype.deploy_candidate_app.deploy_candidate_app import DeployCandidateApp
	from press.press.doctype.press_settings.press_settings import PressSettings

# Long enough for a build to wait in the agent's queue, run, and push
SIGNED_URL_EXPIRY = 12 * 60 * 60


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


def get_asset_store_instructions(apps: list[DeployCandidateApp], can_upload: bool) -> list[dict[str, str]]:
	"""Signed URLs the agent uses around the build, so the build itself never reaches the store.
	Only builds that can upload get upload URLs; the others just build what isn't stored."""
	try:
		client, bucket = _get_asset_store()
		instructions = []
		for app in apps:
			if app.app == "frappe" or not app.use_cached:
				continue

			file_name = f"{app.app}.{app.hash}.tar.gz"
			if asset_exists(client, bucket, file_name):
				url = {"download_url": sign_url(client, "get_object", bucket, file_name)}
			elif can_upload:
				url = {"upload_url": sign_url(client, "put_object", bucket, file_name)}
			else:
				continue
			instructions.append({"app": app.app, "hash": app.hash, **url})
	except Exception:
		# The build then builds every app's assets itself
		frappe.log_error("Asset store unavailable")
		return []

	return instructions


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
