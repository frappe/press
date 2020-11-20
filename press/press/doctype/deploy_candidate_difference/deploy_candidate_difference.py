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
from press.api.github import get_access_token


class DeployCandidateDifference(Document):
	def validate(self):
		if self.source == self.destination:
			frappe.throw(
				"Destination Candidate must be different from Source Candidate",
				frappe.ValidationError,
			)

		source_creation = frappe.db.get_value("Deploy Candidate", self.source, "creation")
		destination_creation = frappe.db.get_value(
			"Deploy Candidate", self.destination, "creation"
		)
		if source_creation > destination_creation:
			frappe.throw(
				"Destination Candidate must be created after Source Candidate",
				frappe.ValidationError,
			)

		if frappe.get_all(
			"Deploy Candidate Difference",
			filters={
				"group": self.group,
				"source": self.source,
				"destination": self.destination,
				"name": ("!=", self.name),
			},
		):
			frappe.throw(
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
		for destination in destination_candidate.applications:
			app = {
				"app": destination.app,
				"destination_release": destination.release,
				"destination_hash": destination.hash,
			}
			source = find(source_candidate.apps, lambda x: x.app == destination.app)
			if source:
				app.update({"source_release": source.release, "source_hash": source.hash})
			self.append("apps", app)
		self.save()
		self.compute_deploy_type()
		self.save()

	def compute_deploy_type(self):
		self.deploy_type = "Pull"
		for app in self.apps:
			if (not app.source_hash) or (app.source_hash == app.destination_hash):
				continue
			app.changed = True
			app.deploy_type = "Pull"
			frappe_app = frappe.get_doc("Application", app.app)
			if frappe_app.installation:
				github_access_token = get_access_token(frappe_app.installation)
				client = Github(github_access_token)
			else:
				client = Github()
			repo = client.get_repo(f"{frappe_app.repo_owner}/{frappe_app.repo}")
			diff = repo.compare(app.source_hash, app.destination_hash)
			app.github_diff_url = diff.html_url
			files = [f.filename for f in diff.files]
			if is_migrate_needed(files):
				self.deploy_type = "Migrate"
				app.deploy_type = "Migrate"
			app.files = json.dumps(files, indent=4)


def is_migrate_needed(files):
	patches_file_regex = re.compile(r"\w+/patches\.txt")
	if any(map(patches_file_regex.match, files)):
		return True

	hooks_regex = re.compile(r"\w+/hooks\.py")
	if any(map(hooks_regex.match, files)):
		return True

	fixtures_regex = re.compile(r"\w+/fixtures/")
	if any(map(fixtures_regex.match, files)):
		return True

	custom_regex = re.compile(r"\w+/\w+/custom/")
	if any(map(custom_regex.match, files)):
		return True

	languages_json = re.compile(r"frappe/geo/languages.json")
	if any(map(languages_json.match, files)):
		return True

	json_regex = re.compile(r"\w+/\w+/\w+/(.+)/\1\.json")
	return any(map(json_regex.match, files))
