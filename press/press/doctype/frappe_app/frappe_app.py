# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from github import Github


class FrappeApp(Document):
	def validate(self):
		*_, self.repo_owner, self.scrubbed = self.url.split("/")

	def after_insert(self):
		self.create_app_release()

	def create_app_release(self):
		github_access_token = frappe.db.get_single_value("Press Settings", "github_access_token")
		if github_access_token:
			client = Github(github_access_token)
		else:
			client = Github()

		repo = client.get_repo(f"{self.repo_owner}/{self.scrubbed}")
		branch = repo.get_branch(self.branch)
		hash = branch.commit.sha
		if not frappe.db.exists("App Release", {"hash": hash}):
			frappe.get_doc({"doctype": "App Release", "app": self.name, "hash": hash}).insert()
