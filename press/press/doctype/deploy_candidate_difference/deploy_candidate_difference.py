# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import re
import json
from frappe.model.document import Document
from frappe.core.utils import find
from github import Github


class DeployCandidateDifference(Document):
	def validate(self):
		if frappe.get_all(
			"Deploy Candidate Difference",
			filters={
				"group": self.group,
				"source": self.source,
				"destination": self.destination,
				"name": ("!=", self.name),
			},
		):
			raise frappe.throw(
				"Deploy Candidate Difference already exists for Release Group: {} "
				", Source Release: {} and Destination Release: {}".format(
					self.group, self.source, self.destination
				),
				frappe.ValidationError,
			)

	def after_insert(self):
		self.populate_apps_table()

	def populate_apps_table(self):
		source_candidate = frappe.get_doc("Deploy Candidate", self.source)
		destination_candidate = frappe.get_doc("Deploy Candidate", self.destination)
		for destination in destination_candidate.apps:
			source = find(source_candidate.apps, lambda x: x.app == destination.app)
			if source:
				app = {
					"app": destination.app,
					"source_release": source.release,
					"source_hash": source.hash,
					"destination_release": destination.release,
					"destination_hash": destination.hash,
				}
				self.append("apps", app)
		self.save()
		self.compute_deploy_type()
		self.save()

	def compute_deploy_type(self):
		github_access_token = frappe.db.get_single_value(
			"Press Settings", "github_access_token"
		)
		if github_access_token:
			client = Github(github_access_token)
		else:
			client = Github()

		self.deploy_type = "Pull"
		for app in self.apps:
			frappe_app = frappe.get_doc("Frappe App", app.app)
			repo = client.get_repo(f"{frappe_app.repo_owner}/{frappe_app.scrubbed}")
			diff = repo.compare(app.source_hash, app.destination_hash)
			app.github_diff_url = diff.html_url
			files = [f.filename for f in diff.files]
			deploy_type = "Migrate" if is_migrate_needed(files) else "Pull"
			if deploy_type == "Migrate":
				self.deploy_type = "Migrate"
			app.deploy_type = deploy_type
			app.files = json.dumps(files, indent=4)


def is_migrate_needed(files):
	patches_file_regex = re.compile(r"\w+/patches\.txt")
	if any(map(patches_file_regex.match, files)):
		return True

	json_regex = re.compile(r"\w+/\w+/\w+/(.+)/\1\.json")
	return any(map(json_regex.match, files))
