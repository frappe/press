# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import json
import boto3
import frappe
from frappe.utils.password import get_decrypted_password
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
			"minio/create",
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
			"minio/update",
			data=data,
		)

	def remove_user(self):
		data = {
			"username": self.access_key,
		}
		agent = Agent(server_type=self.SERVER_TYPE, server=self.minio_server_on)

		return agent.create_agent_job(
			"Remove Minio User",
			"minio/remove",
			data=data,
		)


def create_after_insert(doc, method):
	if doc.app == "storage_integration":
		frappe.get_doc(
			{"doctype": "Storage Integration Subscription", "site": doc.site}
		).insert()
	elif doc.app == "email_delivery_service":
		from press.api.email import setup

		setup(doc.site)

		frappe.db.commit()


def monitor_storage():
	active_subs = frappe.get_all(
		"Storage Integration Subscription", fields=["site", "name"], filters={"enabled": 1}
	)
	access_key = frappe.db.get_value("Add On Settings", None, "aws_access_key")
	secret_key = get_decrypted_password(
		"Add On Settings", "Add On Settings", "aws_secret_key"
	)

	for sub in active_subs:
		size = get_size("bucket_name", sub["site"], access_key, secret_key)
		# not used yet
		if size == 0:
			break

		doc = frappe.get_doc("Storage Integration Subscription", sub["name"])
		if doc.usage > doc.limit:
			# send emails maybe?
			doc.update_user("disable")
			doc.enabled = 0
		else:
			doc.usage = size

		doc.save()
		frappe.db.commit()


def get_size(bucket, path, access_key, secret_key):
	s3 = boto3.resource(
		"s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key
	)
	my_bucket = s3.Bucket(bucket)
	total_size = 0

	for obj in my_bucket.objects.filter(Prefix=path):
		total_size = total_size + obj.size

	return total_size


@frappe.whitelist()
def update_user_status(docname, status):
	doc = frappe.get_doc("Storage Integration Subscription", docname)
	status = int(status)

	if status == 0:
		doc.update_user("disable")
	elif status == 1:
		doc.update_user("enable")

	frappe.db.commit()
