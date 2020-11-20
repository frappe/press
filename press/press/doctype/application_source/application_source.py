# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.api.github import get_access_token
from press.utils import log_error
import requests


class ApplicationSource(Document):
	def after_insert(self):
		self.create_release()

	def on_update(self):
		self.create_release()

	def validate(self):
		self.validate_source_signature()

	def validate_source_signature(self):
		# Don't allow multiple sources with same signature
		if frappe.db.exists(
			"Application Source",
			{
				"name": ("!=", self.name),
				"application": self.application,
				"version": self.version,
				"repository_url": self.repository_url,
				"branch": self.branch,
			},
		):
			frappe.throw(
				f"Duplicate source {(self.version, self.repository_url, self.branch)}"
				f" for {self.application}",
				frappe.ValidationError,
			)

	def before_save(self):
		# Assumes repository_url looks like https://github.com/frappe/erpnext
		_, self.repository_owner, self.repository = self.repository_url.rsplit("/", 2)
		# self.create_release()

	def create_release(self):
		try:
			if self.github_installation_id:
				token = get_access_token(self.github_installation_id)
				headers = {
					"Authorization": f"token {token}",
				}
			else:
				headers = {}
			branch = requests.get(
				f"https://api.github.com/repos/{self.repository_owner}/{self.repository}/branches/{self.branch}",
				headers=headers,
			).json()
			hash = branch["commit"]["sha"]
			if not frappe.db.exists(
				"Application Release", {"app": self.application, "source": self.name, "hash": hash}
			):
				is_first_release = (
					0  # frappe.db.count("Application Release", {"app": self.name}) == 0
				)
				frappe.get_doc(
					{
						"doctype": "Application Release",
						"app": self.application,
						"source": self.name,
						"hash": hash,
						"message": branch["commit"]["commit"]["message"],
						"author": branch["commit"]["commit"]["author"]["name"],
						"deployable": bool(is_first_release),
					}
				).insert()
		except Exception:
			log_error("App Release Creation Error", app=self.name)
