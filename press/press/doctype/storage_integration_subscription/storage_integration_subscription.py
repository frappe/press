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

	def create_user(self):
		agent = Agent(server_type=self.SERVER_TYPE, server=self.minio_server_on)
		data = {
			"access_key": self.access_key,
			"secret_key": self.secret_key,
			"policy_name": self.policy_name,
			"policy_json": self.policy_json,
		}

		return agent.create_agent_job(
			"Create Minio User",
			f"minio/create",
			data=data,
		)

	def update_user(self, op_type):
		"""
		param op_type: type of operation 'enable' or 'disable'
		"""
		data = {"username": self.access_key, "type": op_type}
		agent = Agent(server_type=self.SERVER_TYPE, server=self.minio_server_on)

		return agent.create_agent_job(
			f"{op_type.capitalize()} Minio User",
			f"minio/subscription",
			data=data,
		)

	def remove_user(self):
		data = {
			"username": self.access_key,
		}
		agent = Agent(server_type=self.SERVER_TYPE, server=self.minio_server_on)

		return agent.create_agent_job(
			"Remove Minio User",
			f"minio/remove",
			data=data,
		)
