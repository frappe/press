# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import json
import frappe
from hashlib import blake2b
from press.agent import Agent
from frappe.model.document import Document


class StorageIntegrationSubscription(Document):
	SERVER_TYPE = "Proxy Server"

	def after_insert(self):
		self.create_user()

	def validate(self):
		self.set_access_key_and_policy_name()
		self.set_secret_key()
		self.set_policy_json()
		self.set_minio_server_on()

	def set_access_key_and_policy_name(self):
		# site.frappe.cloud -> site_frappe_cloud
		self.access_key = self.name
		self.policy_name = self.access_key + "_policy"

	def set_secret_key(self):
		h = blake2b(digest_size=12)
		h.update(self.name.encode())
		self.secret_key = h.hexdigest()

	def set_policy_json(self):
		data = {
			"Version": "2012-10-17",
			"Statement": [
				{
					"Effect": "Allow",
					"Action": ["s3:GetObject", "s3:PutObject"],
					"Resource": f"arn:aws:s3:::dev.storage.frappe.cloud/{self.site}/*",
				}
			],
		}
		self.policy_json = json.dumps(data, indent=4)

	def set_minio_server_on(self):
		server = frappe.db.get_value("Site", self.site, "server")
		self.minio_server_on = frappe.db.get_value("Server", server, "proxy_server")
