# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from boto3 import client, resource
from botocore.exceptions import ClientError

import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password


def get_remote_key(file):
	from press.utils import get_current_team
	from hashlib import sha1
	from os.path import join
	from time import time

	team = sha1(get_current_team().encode()).hexdigest()
	time = str(time()).replace(".", "_")

	return join(team, time, file)


def poll_file_statuses():
	available_files = {}
	doctype = "Remote File"
	buckets = {
		"backups": {
			"bucket": frappe.db.get_single_value("Press Settings", "aws_s3_bucket"),
			"access_key_id": frappe.db.get_single_value(
				"Press Settings", "offsite_backups_access_key_id"
			),
			"secret_access_key": get_decrypted_password(
				"Press Settings", "Press Settings", "offsite_backups_secret_access_key"
			),
			"tag": "Offsite Backup",
		},
		"uploads": {
			"bucket": frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"),
			"access_key_id": frappe.db.get_single_value(
				"Press Settings", "remote_access_key_id"
			),
			"secret_access_key": get_decrypted_password(
				"Press Settings", "Press Settings", "remote_secret_access_key"
			),
			"tag": "Site Upload",
		},
	}

	for bucket in buckets:
		current_bucket = buckets[bucket]
		available_files[current_bucket["bucket"]] = []

		s3 = resource(
			"s3",
			aws_access_key_id=current_bucket["access_key_id"],
			aws_secret_access_key=current_bucket["secret_access_key"],
			region_name="ap-south-1",
		)

		for s3_object in s3.Bucket(current_bucket["bucket"]).objects.all():
			available_files[current_bucket["bucket"]].append(s3_object.key)

		all_files = tuple(available_files[current_bucket["bucket"]])

		remote_files = frappe.get_all(
			doctype,
			fields=["name", "file_path", "status"],
			filters={"_user_tags": ("like", f"%{current_bucket['tag']}%")},
		)

		for remote_file in remote_files:
			name, file_path, status = (
				remote_file["name"],
				remote_file["file_path"],
				remote_file["status"],
			)
			if file_path not in all_files:
				if status == "Available":
					frappe.db.set_value(doctype, name, "status", "Unavailable")
			else:
				if status == "Unavailable":
					frappe.db.set_value(doctype, name, "status", "Available")

		frappe.db.commit()


class RemoteFile(Document):
	@property
	def s3_client(self):
		if self.bucket == frappe.db.get_single_value("Press Settings", "aws_s3_bucket"):
			access_key_id = frappe.db.get_single_value(
				"Press Settings", "offsite_backups_access_key_id"
			)
			secret_access_key = get_decrypted_password(
				"Press Settings", "Press Settings", "offsite_backups_secret_access_key"
			)

		elif self.bucket == frappe.db.get_single_value(
			"Press Settings", "remote_uploads_bucket"
		):
			access_key_id = frappe.db.get_single_value("Press Settings", "remote_access_key_id")
			secret_access_key = get_decrypted_password(
				"Press Settings", "Press Settings", "remote_secret_access_key"
			)

		else:
			raise Exception("Credentials for the bucket don't exist!")

		return client(
			"s3",
			aws_access_key_id=access_key_id,
			aws_secret_access_key=secret_access_key,
			region_name="ap-south-1",
		)

	@property
	def download_link(self):
		return self.get_download_link()

	def exists(self):
		try:
			return self.s3_client.head_object(Bucket=self.bucket, Key=self.file_path)
		except ClientError:
			return False

	def delete_remote_object(self):
		self.db_set("status", "Unavailable")
		return self.s3_client.delete_object(
			Bucket=frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"),
			Key=self.file_path,
		)

	def on_trash(self):
		self.delete_remote_object()

	def get_download_link(self):
		return self.s3_client.generate_presigned_url(
			"get_object",
			Params={"Bucket": self.bucket, "Key": self.file_path},
			ExpiresIn=frappe.db.get_single_value("Press Settings", "remote_link_expiry") or 3600,
		)
