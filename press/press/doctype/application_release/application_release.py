# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import os
import shlex
import shutil
import subprocess
import frappe
from frappe.model.document import Document
from press.api.github import get_access_token
from press.utils import log_error


class ApplicationRelease(Document):
	def after_insert(self):
		self.create_deploy_candidates()
		self.create_release_differences()

	def create_deploy_candidates(self):
		candidates = frappe.get_all(
			"Deploy Candidate Application Release",
			fields=["parent"],
			filters={"application": self.application, "release": self.name},
		)
		if candidates:
			return

		for group_app in frappe.get_all(
			"Release Group Application",
			fields=["parent"],
			filters={"application": self.application},
		):
			group = frappe.get_doc("Release Group", group_app.parent)
			group.create_deploy_candidate()

	def clone(self):
		frappe.enqueue_doc(self.doctype, self.name, "_clone")

	def _clone(self):
		try:
			if self.cloned:
				return
			self._prepare_clone_directory()
			self._clone_repo()
			self.cloned = True
			self.save()
		except Exception:
			log_error("Application Release Clone Exception", release=self.name)

	def run(self, command):
		try:
			return subprocess.check_output(
				shlex.split(command), stderr=subprocess.STDOUT, cwd=self.clone_directory
			).decode()
		except Exception as e:
			log_error(
				"Application Release Clone Exception", command=command, output=e.output.decode()
			)
			raise e

	def _prepare_clone_directory(self):
		clone_directory = frappe.db.get_single_value("Press Settings", "clone_directory")
		code_server = frappe.db.get_single_value("Press Settings", "code_server")
		if not os.path.exists(clone_directory):
			os.mkdir(clone_directory)

		app_directory = os.path.join(clone_directory, self.application)
		if not os.path.exists(app_directory):
			os.mkdir(app_directory)

		self.clone_directory = os.path.join(clone_directory, self.application, self.hash[:10])
		if not os.path.exists(self.clone_directory):
			os.mkdir(self.clone_directory)

		code_server_url = (
			f"{code_server}/?folder=/home/coder/project/{self.application}/{self.hash[:10]}"
		)
		self.code_server_url = code_server_url

	def _clone_repo(self):
		source = frappe.get_doc("Application Source", self.source)
		if source.github_installation_id:
			token = get_access_token(source.github_installation_id)
			url = f"https://x-access-token:{token}@github.com/{source.repository_owner}/{source.repository}"
		else:
			url = source.repository_url
		self.output = ""
		self.output += self.run("git init")
		self.output += self.run(f"git checkout -b {source.branch}")
		self.output += self.run(f"git remote add origin {url}",)
		self.output += self.run("git config credential.helper ''")
		self.output += self.run(f"git fetch --depth 1 --progress origin {self.hash}")
		self.output += self.run(f"git checkout {self.hash}")
		self.output += self.run(f"git reset --hard {self.hash}")

	def on_trash(self):
		if self.clone_directory and os.path.exists(self.clone_directory):
			shutil.rmtree(self.clone_directory)

	def create_release_differences(self):
		releases = frappe.get_all(
			"Application Release",
			{"application": self.application, "source": self.source, "name": ("!=", self.name)},
		)
		for release in releases:
			difference = frappe.get_doc(
				{
					"doctype": "Application Release Difference",
					"application": self.application,
					"source": self.source,
					"source_release": release.name,
					"destination_release": self.name,
				}
			)
			difference.insert()
