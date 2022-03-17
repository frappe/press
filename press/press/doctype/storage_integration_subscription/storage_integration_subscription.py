# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import json
import boto3
import frappe
import math
from frappe.utils.password import get_decrypted_password
from hashlib import blake2b
from press.agent import Agent
from frappe.model.document import Document


class StorageIntegrationSubscription(Document):
	SERVER_TYPE = "Proxy Server"

	def after_insert(self):
		self.create_user()

	def validate(self):
		self.set_minio_server_on()
		self.set_access_key_and_policy_name()
		self.set_secret_key()
		self.set_policy_json()

	def set_access_key_and_policy_name(self):
		# site.frappe.cloud -> site_frappe_cloud
		self.access_key = self.name
		self.policy_name = self.access_key + "_policy"

	def set_secret_key(self):
		h = blake2b(digest_size=20)
		h.update(self.name.encode())
		self.secret_key = h.hexdigest()

	def set_policy_json(self):
		bucket_name = frappe.db.get_value(
			"Storage Integration Bucket", self.minio_server_on, "bucket_name"
		)
		data = {
			"Version": "2012-10-17",
			"Statement": [
				{
					"Effect": "Allow",
					"Action": ["s3:GetObject", "s3:PutObject"],
					"Resource": f"arn:aws:s3:::{bucket_name}/{self.site}/*",
				}
			],
		}
		self.policy_json = json.dumps(data, indent=4)

	def set_minio_server_on(self):
		server = frappe.db.get_value("Site", self.site, "server")
		self.minio_server_on = frappe.db.get_value("Server", server, "proxy_server")

	def create_user(self):
		print("Creating Userssssssss")
		agent = Agent(server_type=self.SERVER_TYPE, server=self.minio_server_on)
		data = {
			"access_key": self.access_key,
			"secret_key": self.secret_key,
			"policy_name": self.policy_name,
			"policy_json": self.policy_json,
		}

		return agent.create_agent_job(
			"Create Minio User",
			"minio/users",
			method="POST",
			data=data,
		)

	def toggle_user(self, action):
		"""
		param op_type: type of operation 'enable' or 'disable'
		"""
		agent = Agent(server_type=self.SERVER_TYPE, server=self.minio_server_on)

		return agent.create_agent_job(
			f"{action.capitalize()} Minio User",
			path=f"/minio/users/{self.access_key}/toggle/{action}",
			method="POST",
		)

	def remove_user(self):
		agent = Agent(server_type=self.SERVER_TYPE, server=self.minio_server_on)

		return agent.create_agent_job(
			"Remove Minio User",
			method="DELETE",
			path=f"minio/users/{self.access_key}",
		)


def create_after_insert(doc, method):
	if not doc.site:
		return

	if doc.app == "storage_integration":
		sub_exists = frappe.db.exists(
			{"doctype": "Storage Integration Subscription", "site": doc.site}
		)
		if sub_exists:
			return

		frappe.get_doc(
			{"doctype": "Storage Integration Subscription", "site": doc.site}
		).insert(ignore_permissions=True)

	if doc.app == "email_delivery_service":
		# TODO: add a separate doctype to track email service setup completion
		from press.api.email import setup

		setup(doc.site)


size_name = ("B", "KB", "MB", "GB", "TB", "PB")


def monitor_storage():
	active_subs = frappe.get_all(
		"Storage Integration Subscription", fields=["site", "name"], filters={"enabled": 1}
	)
	access_key = frappe.db.get_value("Add On Settings", None, "aws_access_key")
	secret_key = get_decrypted_password(
		"Add On Settings", "Add On Settings", "aws_secret_key"
	)

	for sub in active_subs:
		usage, unit_u = get_size("bucket_name", sub["site"], access_key, secret_key)
		# not used yet
		if usage == 0:
			break

		doc = frappe.get_doc("Storage Integration Subscription", sub["name"])
		limit, unit_l = doc.limit.split(" ")

		# TODO: Add size_name index change when there are very higher plans
		if unit_u == unit_l and usage >= int(limit):
			# send emails maybe?
			doc.toggle_user("disable")
			doc.enabled = 0
		else:
			doc.usage = f"{usage} {unit_u}"

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

	return convert_size(total_size)


def convert_size(size_bytes):
	if size_bytes == 0:
		return 0, "B"
	i = int(math.floor(math.log(size_bytes, 1024)))
	p = math.pow(1024, i)
	s = round(size_bytes / p, 2)
	return s, size_name[i]


@frappe.whitelist()
def toggle_user_status(docname, status):
	doc = frappe.get_doc("Storage Integration Subscription", docname)
	status = int(status)

	if status == 0:
		doc.toggle_user("disable")
	elif status == 1:
		doc.toggle_user("enable")

	frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def get_analytics(**data):
	from press.api.developer.marketplace import get_subscription_status

	if get_subscription_status(data["secret_key"]) != "Active":
		return

	site, available = frappe.db.get_value(
		"Storage Integration Subscription", data["access_key"], ["site", "limit"]
	)
	access_key = frappe.db.get_value("Add On Settings", None, "aws_access_key")
	secret_key = get_decrypted_password(
		"Add On Settings", "Add On Settings", "aws_secret_key"
	)
	used, unit_u = get_size(data["bucket"], site, access_key, secret_key)

	return {"used": f"{used} {unit_u}", "available": available}
