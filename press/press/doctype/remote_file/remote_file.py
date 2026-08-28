# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import pprint
from typing import TYPE_CHECKING

import frappe
import requests
from boto3 import client, resource
from frappe import _
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password

from press.press.doctype.site_activity.site_activity import log_site_activity

if TYPE_CHECKING:
	from press.press.doctype.backup_bucket.backup_bucket import BackupBucket


def get_team_prefix(team: str) -> str:
	"""Every uploaded file is keyed under a prefix derived from the team."""
	from hashlib import sha1

	return sha1(team.encode()).hexdigest()


def get_remote_key(file):
	from os.path import basename
	from time import time

	from press.utils import get_current_team

	prefix = get_team_prefix(get_current_team())
	timestamp = str(time()).replace(".", "_")

	# basename, because join() drops the prefix when file is an absolute path
	return f"{prefix}/{timestamp}/{basename(file)}"


def validate_files_belong_to_team(files: dict, team: str):
	"""Restore accepts Remote File names from the client. They must be the team's own."""
	for key in ("database", "public", "private", "config"):
		name = files.get(key)
		if not name:
			continue

		# A file with no team has no established owner, so it is never the site's
		file_team = frappe.db.get_value("Remote File", name, "team")
		if file_team != team:
			frappe.throw(
				_("Remote File {0} does not belong to site's team").format(name),
				frappe.PermissionError,
			)


def poll_file_statuses():
	aws_access_key = frappe.db.get_single_value("Press Settings", "offsite_backups_access_key_id")
	aws_secret_key = get_decrypted_password(
		"Press Settings", "Press Settings", "offsite_backups_secret_access_key"
	)
	default_region = frappe.db.get_single_value("Press Settings", "backup_region")
	buckets = [
		{
			"name": frappe.db.get_single_value("Press Settings", "aws_s3_bucket"),
			"region": default_region,
			"access_key_id": aws_access_key,
			"secret_access_key": aws_secret_key,
		},
		{
			"name": frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"),
			"region": default_region,
			"access_key_id": frappe.db.get_single_value("Press Settings", "remote_access_key_id"),
			"secret_access_key": get_decrypted_password(
				"Press Settings", "Press Settings", "remote_secret_access_key"
			),
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
		return None

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
	frappe.db.set_value("Remote File", {"name": ("in", remote_files)}, "status", "Unavailable")

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
		team: DF.Link | None
		url: DF.Code | None
	# end: auto-generated types

	def before_validate(self):
		self.ensure_team_set()

	def ensure_team_set(self):
		if self.team:
			return

		if self.site:
			# Backup remote files are created in agent job callbacks, where the
			# session user is Administrator. The site's team is the owner there.
			self.team = frappe.db.get_value("Site", self.site, "team")

		if not self.team:
			from press.utils import get_current_team

			self.team = get_current_team()

	def validate(self):
		self.validate_upload_prefix()

	def validate_upload_prefix(self):
		"""An uploaded file must sit under its team's prefix.

		The path comes from the client, and the restore flow later hands it to
		the agent as a presigned link.
		"""
		if not self.is_new() or not self.file_path:
			return

		uploads_bucket = frappe.db.get_single_value("Press Settings", "remote_uploads_bucket")
		if not uploads_bucket or self.bucket != uploads_bucket:
			return

		if not self.team:
			frappe.throw(_("Uploaded file must belong to a team"), frappe.PermissionError)

		prefix = get_team_prefix(self.team)
		if not self.file_path.startswith(f"{prefix}/"):
			frappe.throw(
				_("File path {0} is not under this team's upload prefix").format(self.file_path),
				frappe.PermissionError,
			)

	@property
	def s3_client(self):
		if not self.bucket:
			return None

		if self.bucket == frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"):
			access_key_id = frappe.db.get_single_value("Press Settings", "remote_access_key_id")
			secret_access_key = get_decrypted_password(
				"Press Settings", "Press Settings", "remote_secret_access_key"
			)

		elif self.bucket:
			access_key_id = frappe.db.get_single_value("Press Settings", "offsite_backups_access_key_id")
			secret_access_key = get_decrypted_password(
				"Press Settings", "Press Settings", "offsite_backups_secret_access_key"
			)

		else:
			return None

		region = frappe.db.get_single_value("Press Settings", "backup_region")
		endpoint_url = None

		if frappe.db.exists("Backup Bucket", self.bucket):
			backup_bucket: BackupBucket = frappe.get_doc("Backup Bucket", self.bucket)
			if backup_bucket.replication_enabled:
				region = backup_bucket.replication_region
				endpoint_url = backup_bucket.replication_endpoint_url or endpoint_url
			else:
				region = backup_bucket.region
				endpoint_url = backup_bucket.endpoint_url or endpoint_url

		return client(
			"s3",
			aws_access_key_id=access_key_id,
			aws_secret_access_key=secret_access_key,
			region_name=region,
			endpoint_url=endpoint_url,
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
		try:
			bucket = self.bucket
			if frappe.db.exists("Backup Bucket", self.bucket):
				backup_bucket: BackupBucket = frappe.get_doc("Backup Bucket", self.bucket)
				if backup_bucket.replication_enabled:
					bucket = backup_bucket.replication_bucket

			return self.s3_client.head_object(Bucket=bucket, Key=self.file_path)
		except Exception:
			self.db_set("status", "Unavailable")
			return False

	@frappe.whitelist()
	def delete_remote_object(self):
		self.db_set("status", "Unavailable")
		return self.s3_client.delete_object(
			Bucket=self.bucket or frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"),
			Key=self.file_path,
		)

	def on_trash(self):
		self.delete_remote_object()

	@frappe.whitelist()
	def get_download_link(self):
		# The `site` field is not set during the upload & restore of files.
		# Not gonna play with the code here.
		# Also, it doesn't make sense to log access while restoring.
		if self.site:
			log_site_activity(site=self.site, action="Access Offsite Backups")
			frappe.db.commit()

		bucket = self.bucket
		if frappe.db.exists("Backup Bucket", bucket):
			backup_bucket: BackupBucket = frappe.get_doc("Backup Bucket", bucket)
			if backup_bucket.replication_enabled:
				bucket = backup_bucket.replication_bucket

		return self.url or self.s3_client.generate_presigned_url(
			"get_object",
			Params={"Bucket": bucket, "Key": self.file_path},
			ExpiresIn=frappe.db.get_single_value("Press Settings", "remote_link_expiry") or 3600,
		)

	def get_content(self):
		if self.url:
			return json.loads(requests.get(self.url).content)

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

		assert self.url, "URL must be set to get file size"
		response = requests.head(self.url)
		self.file_size = int(response.headers.get("content-length", 0))
		self.save()
		return int(self.file_size)


def delete_s3_files(buckets):
	"""Delete specified files from s3 buckets"""
	from boto3 import resource

	from press.utils import chunk

	press_settings = frappe.get_single("Press Settings")
	for bucket_name in buckets:
		endpoint_url = (
			frappe.db.get_value("Backup Bucket", bucket_name, "endpoint_url") or "https://s3.amazonaws.com"
		)
		if "s3.me-south-1.amazonaws.com" in endpoint_url:
			continue

		s3 = resource(
			"s3",
			aws_access_key_id=press_settings.offsite_backups_access_key_id,
			aws_secret_access_key=press_settings.get_password(
				"offsite_backups_secret_access_key", raise_exception=False
			),
			endpoint_url=endpoint_url,
		)
		bucket = s3.Bucket(bucket_name)
		for objects in chunk([{"Key": x} for x in buckets[bucket_name]], 1000):
			response = bucket.delete_objects(Delete={"Objects": objects})
			response = pprint.pformat(response)
			frappe.get_doc(
				doctype="Remote Operation Log", operation_type="Delete Files", response=response
			).insert()
