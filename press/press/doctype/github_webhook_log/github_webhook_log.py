# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
import hmac
import hashlib
import json
from frappe.model.document import Document
from press.utils import log_error


class GitHubWebhookLog(Document):
	def validate(self):
		secret = frappe.db.get_single_value("Press Settings", "github_webhook_secret")
		digest = hmac.HMAC(secret.encode(), self.payload.encode(), hashlib.sha1)
		if not hmac.compare_digest(digest.hexdigest(), self.signature):
			frappe.throw("Invalid Signature")

		payload = self.parsed_payload
		repository = payload.repository
		installation = payload.installation
		if installation:
			self.github_installation_id = installation["id"]

		if payload.repository:
			self.repository = repository["name"]
			self.repository_owner = repository["owner"]["login"]

		if self.event == "push":
			ref_types = {"tags": "tag", "heads": "branch"}
			self.git_reference_type = ref_types[payload.ref.split("/")[1]]
			ref = payload.ref.split("/", 2)[2]
			if self.git_reference_type == "tag":
				self.tag = ref
			elif self.git_reference_type == "branch":
				self.branch = ref
		elif self.event == "create":
			self.git_reference_type = payload.ref_type
			if self.git_reference_type == "tag":
				self.tag = payload.ref
			elif self.git_reference_type == "branch":
				self.branch = payload.ref

		self.payload = json.dumps(payload, indent=4, sort_keys=True)

	def after_insert(self):
		payload = self.parsed_payload
		if self.event == "push":
			if self.git_reference_type == "branch":
				self.create_app_release(payload)
			elif self.git_reference_type == "tag":
				self.create_app_tag(payload)

	@property
	def parsed_payload(self):
		return frappe.parse_json(self.payload)

	def create_app_release(self, payload):
		try:
			source = frappe.get_value(
				"App Source",
				{
					"branch": self.branch,
					"repository": self.repository,
					"repository_owner": self.repository_owner,
				},
				["name", "app"],
				as_dict=True,
			)
			if source:
				commit = payload.head_commit
				release = frappe.get_doc(
					{
						"doctype": "App Release",
						"app": source.app,
						"source": source.name,
						"hash": commit["id"],
						"message": commit["message"],
						"author": commit["author"]["name"],
					}
				)
				release.insert()
		except Exception:
			log_error("App Release Creation Error", payload=payload)

	def create_app_tag(self, payload):
		try:
			commit = payload.head_commit
			tag = frappe.get_doc(
				{
					"doctype": "App Tag",
					"tag": self.tag,
					"hash": commit["id"],
					"repository": self.repository,
					"repository_owner": self.repository_owner,
					"github_installation_id": self.github_installation_id,
				}
			)
			tag.insert()
		except Exception:
			log_error("App Tag Creation Error", payload=payload)
