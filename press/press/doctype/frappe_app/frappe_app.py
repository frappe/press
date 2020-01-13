# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from github import Github

class FrappeApp(Document):
	def validate(self):
		self.create_app_release()

	def create_app_release(self):
		client = Github()
		repo = client.get_repo(f"{self.repo_owner}/{self.scrubbed}")
		branch = repo.get_branch(self.branch)
		hash = branch.commit.sha
		if not frappe.db.exists("App Release", {"hash": hash}):
			frappe.get_doc({
				"doctype": "App Release",
				"app": self.name,
				"hash": hash
			}).insert()
			