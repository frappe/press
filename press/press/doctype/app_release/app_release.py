# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import subprocess
import frappe
from frappe.model.document import Document
from press.api.github import get_access_token
from press.utils import log_error


class AppRelease(Document):
	def after_insert(self):
		auto_approve = frappe.db.get_value("Frappe App", self.app, "auto_approve")
		if auto_approve:
			self.status = "Approved"
			self.save()
		self.create_deploy_candidates()

	def create_deploy_candidates(self):
		for group_app in frappe.get_all(
			"Release Group Frappe App", fields=["parent"], filters={"app": self.app}
		):
			group = frappe.get_doc("Release Group", group_app.parent)
			group.create_deploy_candidate()

	def deploy(self):
		if self.status == "Approved":
			pass

	def request_approval(self):
		if self.status == "":
			self.status = "Awaiting Approval"
			self.save()
			frappe.enqueue_doc(
				self.doctype, self.name, "clone_locally", enqueue_after_commit=True
			)

	def approve(self):
		if self.status == "Awaiting Approval":
			self.status = "Approved"
			self.save()

	def reject(self, reason):
		if self.status == "Awaiting Approval":
			self.status = "Rejected"
			self.save()

	def clone_locally(self):
		try:
			directory = "/home/aditya/Frappe/benches/press/clones"
			if not os.path.exists(directory):
				os.mkdir(directory)

			self.directory = os.path.join(directory, self.hash[:10])
			self.save()
			if not os.path.exists(self.directory):
				os.mkdir(self.directory)

			app = frappe.get_doc("Frappe App", self.app)
			token = get_access_token(app.installation)

			subprocess.run("git init".split(), check=True, cwd=self.directory)
			subprocess.run(
				f"git remote add origin https://x-access-token:{token}@github.com/{app.repo_owner}/{app.repo}".split(),
				check=True,
				cwd=self.directory,
			)
			subprocess.run(
				f"git fetch --depth 1 origin {self.hash}".split(), check=True, cwd=self.directory
			)
			subprocess.run(f"git checkout {self.hash}".split(), check=True, cwd=self.directory)
		except Exception:
			log_error("Clone Error", release=self.name)
