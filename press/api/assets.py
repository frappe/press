from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import boto3
import botocore.exceptions
import frappe

if TYPE_CHECKING:
	from apps.press.press.press.doctype.press_settings.press_settings import PressSettings


@frappe.whitelist()
def upload_asset():
	files = frappe.request.files

	if not files or "asset_file" not in files:
		frappe.throw("No asset file uploaded")

	asset_file = files["asset_file"]

	settings: PressSettings = frappe.get_cached_doc("Press Settings")
	secret_access_key = settings.get_password("asset_store_secret_access_key")
	access_key = settings.asset_store_access_key
	region_name = settings.asset_store_region
	endpoint_url = settings.asset_store_endpoint
	bucket_name = settings.asset_store_bucket_name

	client = boto3.client(
		"s3",
		region_name=region_name,
		endpoint_url=endpoint_url,
		aws_access_key_id=access_key,
		aws_secret_access_key=secret_access_key,
	)
	with contextlib.suppress(botocore.exceptions.ClientError):
		client.head_object(Bucket=bucket_name, Key=asset_file.filename)
		frappe.throw(
			f"Asset for commit hash '{asset_file.filename}' already exists please create a new commit"
		)

	client.upload_fileobj(
		Fileobj=asset_file.stream,
		Bucket=bucket_name,
		Key=asset_file.filename,
		ExtraArgs={
			"ContentType": "application/x-tar",
		},
	)
