# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from boto3 import client
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
	doctype = "Remote File"
	for d in frappe.get_all(doctype):
		doc = frappe.get_doc(doctype, d["name"])
		current_status = "Available" if doc.exists() else "Unavailable"
		if current_status != doc.status:
			doc.status = current_status
			doc.save()


class RemoteFile(Document):
	@property
	def s3_client(self):
		return client(
			"s3",
			aws_access_key_id=frappe.db.get_single_value(
				"Press Settings", "remote_access_key_id"
			),
			aws_secret_access_key=get_decrypted_password(
				"Press Settings", "Press Settings", "remote_secret_access_key"
			),
			region_name="ap-south-1",
		)

	@property
	def download_link(self):
		return self.get_download_link()

	def exists(self):
		try:
			return self.s3_client.head_object(Bucket=self.get_bucket(), Key=self.file_path)
		except ClientError:
			return False

	def get_bucket(self):
		return frappe.db.get_single_value("Press Settings", "remote_uploads_bucket")

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
			Params={"Bucket": self.get_bucket(), "Key": self.file_path},
			ExpiresIn=frappe.db.get_single_value("Press Settings", "remote_link_expiry") or 3600,
		)
