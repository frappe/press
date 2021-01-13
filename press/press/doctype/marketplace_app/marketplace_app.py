# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import requests
import frappe
from base64 import b64decode
from frappe.website.website_generator import WebsiteGenerator
from press.api.github import get_access_token
from frappe.website.utils import cleanup_page_name


class MarketplaceApp(WebsiteGenerator):
	def autoname(self):
		self.name = self.app

	def before_insert(self):
		self.long_description = self.fetch_readme()

	def set_route(self):
		self.route = "marketplace/apps/" + cleanup_page_name(self.title)

	def validate(self):
		self.published = self.status == "Published"

	def get_app_source(self):
		return frappe.get_doc("App Source", {"app": self.app})

	def fetch_readme(self):
		source = self.get_app_source()

		if source.github_installation_id:
			github_access_token = get_access_token(source.github_installation_id)
		else:
			github_access_token = frappe.get_value("Press Settings", None, "github_access_token")

		headers = {
			"Authorization": f"token {github_access_token}",
		}
		owner = source.repository_owner
		repository = source.repository
		branch = source.branch

		readme_content = None
		variants = ["README.md", "readme.md", "readme", "README", "Readme"]
		for variant in variants:
			try:
				readme = requests.get(
					f"https://api.github.com/repos/{owner}/{repository}/contents/{variant}",
					headers=headers,
					params={"ref": branch},
				).json()
				readme_content = b64decode(readme["content"]).decode()
				if readme_content:
					break
			except Exception:
				print(frappe.get_traceback())
				continue

		return readme_content

	def get_context(self, context):
		context.no_cache = True
		context.app = self
		if self.category:
			context.category = frappe.get_doc("Marketplace App Category", self.category)

		groups = frappe.db.get_all(
			"Release Group",
			filters=[
				["Release Group", "enabled", "=", 1],
				["Release Group", "public", "=", 1],
				["Release Group App", "app", "=", self.app],
			],
		)
		for group in groups:
			group_doc = frappe.get_doc("Release Group", group.name)
			frappe_source = frappe.db.get_value(
				"App Source", group_doc.apps[0].source, ["repository_url", "branch"], as_dict=True
			)
			group["frappe"] = frappe_source
			group["version"] = group_doc.version
		context.groups = groups
