# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import json
import pprint
from typing import TYPE_CHECKING

import frappe
import requests
from boto3 import client, resource
from frappe.model.document import Document


if TYPE_CHECKING:
	from press.press.doctype.press_settings.press_settings import PressSettings


def get_remote_key(file):
	from hashlib import sha1
	from os.path import join
	from time import time

	from press.utils import get_current_team

	team = sha1(get_current_team().encode()).hexdigest()
	time = str(time()).replace(".", "_")

	return join(team, time, file)


def poll_file_statuses():
	press_settings: "PressSettings" = frappe.get_single("Press Settings")  # type: ignore

	aws_access_key = press_settings.offsite_backups_access_key_id
	aws_secret_key = press_settings.offsite_backups_secret_access_key
	default_region = press_settings.backup_region

	buckets = [
		{
			"name": press_settings.aws_s3_bucket,
			"region": default_region,
			"access_key_id": aws_access_key,
			"secret_access_key": aws_secret_key,
		},
		{
			"name": press_settings.remote_uploads_bucket,
			"region": press_settings.get("remote_uploads_region") or "ap-south-1",
			"access_key_id": press_settings.remote_access_key_id,
			"secret_access_key": press_settings.get_password("remote_secret_access_key"),
			"endpoint_url": press_settings.get("remote_uploads_endpoint") or None,
		},
	]

	for b in frappe.get_all("Backup Bucket", ["bucket_name", "cluster", "region"]):
		buckets.append(
			{
				"name": b["bucket_name"],
				"region": b["region"],
				"access_key_id": aws_access_key,
				"secret_access_key": aws_secret_key,
			}
		)

	for bucket in buckets:
		frappe.enqueue(
			"press.press.doctype.remote_file.remote_file.poll_file_statuses_from_bucket",
			bucket=bucket,
			job_id=f"poll_file_statuses:{bucket['name']}",
			queue="long",
			deduplicate=True,
			enqueue_after_commit=True,
		)


def poll_file_statuses_from_bucket(bucket):
	from press.utils import chunk

	s3 = resource(
		"s3",
		aws_access_key_id=bucket["access_key_id"],
		aws_secret_access_key=bucket["secret_access_key"],
		region_name=bucket["region"],
		endpoint_url=bucket.get("endpoint_url") or None,
	)

	available_files = set()
	for s3_object in s3.Bucket(bucket["name"]).objects.all():
		available_files.add(s3_object.key)

	doctype = "Remote File"
	remote_files = frappe.get_all(
		doctype,
		fields=["name", "file_path", "status"],
		filters={"bucket": bucket["name"]},
	)

	set_to_available = []
	set_to_unavailable = []
	for remote_file in remote_files:
		name, file_path, status = (
			remote_file["name"],
			remote_file["file_path"],
			remote_file["status"],
		)
		if file_path not in available_files:
			if status == "Available":
				set_to_unavailable.append(name)
		else:
			if status == "Unavailable":
				set_to_available.append(name)

	for files in chunk(set_to_unavailable, 1000):
		frappe.db.set_value(doctype, {"name": ("in", files)}, "status", "Unavailable")

	for files in chunk(set_to_available, 1000):
		frappe.db.set_value(doctype, {"name": ("in", files)}, "status", "Available")

	# Delete s3 files that are not tracked with Remote Files
	remote_file_paths = set(file["file_path"] for file in remote_files)
	file_only_on_s3 = available_files - remote_file_paths
	delete_s3_files({bucket["name"]: list(file_only_on_s3)})
	frappe.db.commit()


def delete_remote_backup_objects(remote_files):
	"""Delete specified objects identified by keys in the backups bucket."""
	remote_files = list(set([x for x in remote_files if x]))
	if not remote_files:
		return

	buckets = {bucket: [] for bucket in frappe.get_all("Backup Bucket", pluck="name")}
	buckets.update({frappe.db.get_single_value("Press Settings", "aws_s3_bucket"): []})

	[
		buckets[bucket].append(file)
		for file, bucket in frappe.db.get_values(
			"Remote File",
			{"name": ("in", remote_files), "status": "Available"},
			["file_path", "bucket"],
		)
	]

	delete_s3_files(buckets)
	frappe.db.set_value(
		"Remote File", {"name": ("in", remote_files)}, "status", "Unavailable"
	)

	return remote_files


class RemoteFile(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bucket: DF.Data | None
		file_name: DF.Data | None
		file_path: DF.Text | None
		file_size: DF.Data | None
		file_type: DF.Data | None
		site: DF.Link | None
		status: DF.Literal["Available", "Unavailable"]
		url: DF.Code | None
	# end: auto-generated types

	@property
	def s3_client(self):
		if not self.bucket:
			return None

		press_settings: "PressSettings" = frappe.get_single("Press Settings")  # type: ignore

		if self.bucket == press_settings.remote_uploads_bucket:
			access_key_id = press_settings.remote_access_key_id
			secret_access_key = press_settings.get_password("remote_secret_access_key")
			region_name = press_settings.get("remote_uploads_region") or "ap-south-1"
			endpoint_url = press_settings.get("remote_uploads_endpoint") or None
		else:
			access_key_id = press_settings.offsite_backups_access_key_id
			secret_access_key = press_settings.get_password("offsite_backups_secret_access_key")
			region_name = (
				frappe.db.get_value("Backup Bucket", self.bucket, "region")
				or press_settings.backup_region
			)
			endpoint_url = (
				frappe.db.get_value("Backup Bucket", self.bucket, "endpoint_url")
				or press_settings.get("offsite_backups_endpoint")
				or None
			)

		return client(
			"s3",
			aws_access_key_id=access_key_id,
			aws_secret_access_key=secret_access_key,
			region_name=region_name,
			endpoint_url=endpoint_url or None,
		)

	@property
	def download_link(self):
		return self.get_download_link()

	@frappe.whitelist()
	def exists(self):
		self.db_set("status", "Available")

		if self.url:
			success = str(requests.head(self.url).status_code).startswith("2")
			if success:
				return True
			self.db_set("status", "Unavailable")
			return False
		else:
			try:
				return self.s3_client.head_object(Bucket=self.bucket, Key=self.file_path)
			except Exception:
				self.db_set("status", "Unavailable")
				return False

	@frappe.whitelist()
	def delete_remote_object(self):
		self.db_set("status", "Unavailable")
		return self.s3_client.delete_object(
			Bucket=frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"),
			Key=self.file_path,
		)

	def on_trash(self):
		self.delete_remote_object()

	@frappe.whitelist()
	def get_download_link(self):
		return self.url or self.s3_client.generate_presigned_url(
			"get_object",
			Params={"Bucket": self.bucket, "Key": self.file_path},
			ExpiresIn=frappe.db.get_single_value("Press Settings", "remote_link_expiry") or 3600,
		)

	def get_content(self):
		if self.url:
			return json.loads(requests.get(self.url).content)
		else:
			obj = self.s3_client.get_object(Bucket=self.bucket, Key=self.file_path)
			return json.loads(obj["Body"].read().decode("utf-8"))

	@property
	def size(self) -> int:
		"""
		Get the size of file in bytes

		Sets the file_size field if not already set
		"""
		if int(self.file_size or 0):
			return int(self.file_size or 0)
		else:
			response = requests.head(self.url)
			self.file_size = int(response.headers.get("content-length", 0))
			self.save()
			return int(self.file_size)


def delete_s3_files(buckets):
	"""Delete specified files from s3 buckets"""
	from boto3 import resource

	from press.utils import chunk

	press_settings = frappe.get_single("Press Settings")
	for bucket_name in buckets.keys():
		s3 = resource(
			"s3",
			aws_access_key_id=press_settings.offsite_backups_access_key_id,
			aws_secret_access_key=press_settings.get_password(
				"offsite_backups_secret_access_key", raise_exception=False
			),
			region_name=frappe.db.get_value("Backup Bucket", bucket_name, "region") or None,
			endpoint_url=frappe.db.get_value("Backup Bucket", bucket_name, "endpoint_url")
			or "https://s3.amazonaws.com",
		)
		bucket = s3.Bucket(bucket_name)
		for objects in chunk([{"Key": x} for x in buckets[bucket_name]], 1000):
			response = bucket.delete_objects(Delete={"Objects": objects})
			response = pprint.pformat(response)
			frappe.get_doc(
				doctype="Remote Operation Log", operation_type="Delete Files", response=response
			).insert()
