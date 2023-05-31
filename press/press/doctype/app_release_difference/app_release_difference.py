# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
import re
import json
from github import Github
from press.api.github import get_access_token


class AppReleaseDifference(Document):
	def validate(self):
		if self.source_release == self.destination_release:
			frappe.throw(
				"Destination Release must be different from Source Release", frappe.ValidationError
			)

	def set_deploy_type(self):
		if self.deploy_type != "Pending":
			return
		self.deploy_type = "Pull"

		source = frappe.get_doc("App Source", self.source)
		if source.github_installation_id:
			try:
				github_access_token = get_access_token(source.github_installation_id)
			except KeyError:
				frappe.throw("Could not get access token for app source {0}".format(source.name))
		else:
			github_access_token = frappe.get_value("Press Settings", None, "github_access_token")

		client = Github(github_access_token)
		try:
			repo = client.get_repo(f"{source.repository_owner}/{source.repository}")
		except Exception:
			frappe.throw("Could not get repository {0}".format(source.repository))
		try:
			diff = repo.compare(self.source_hash, self.destination_hash)
			self.github_diff_url = diff.html_url

			files = [f.filename for f in diff.files]
		except Exception:
			files = ["frappe/geo/languages.json"]

		if is_migrate_needed(files):
			self.deploy_type = "Migrate"

		self.files = json.dumps(files, indent=4)
		self.save()


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
