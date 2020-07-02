# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from boto3 import client

import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password


def get_remote_key(file):
	from hashlib import sha1
	from frappe.utils import getdate, today
	from press.utils import get_current_team
	from os.path import join

	team = get_current_team()
	date = str(getdate(today()))
	key = (team + date).encode()
	hash = sha1(key).hexdigest()

	return join(hash, file)


class RemoteFile(Document):
	@property
	def s3_client(self):
		return client(
			"s3",
			aws_access_key_id=frappe.db.get_single_value("Press Settings", "remote_access_key_id"),
			aws_secret_access_key=get_decrypted_password("Press Settings", "Press Settings", "remote_secret_access_key"),
			region_name="ap-south-1"
		)

	@property
	def download_link(self):
		return self.get_download_link()

	def on_trash(self):
		return self.s3_client.delete_object(
			Bucket=frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"),
			Key=self.file_path
		)

	def get_download_link(self):
		return self.s3_client.generate_presigned_url(
			"get_object",
			Params={
				"Bucket": frappe.db.get_single_value("Press Settings", "remote_uploads_bucket"),
				"Key": self.file_path
			},
			ExpiresIn=frappe.db.get_single_value("Press Settings", "remote_link_expiry") or 3600
		)
