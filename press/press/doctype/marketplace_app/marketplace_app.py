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

	def get_frappe_app(self):
		return frappe.get_doc("App", {"scrubbed": self.name, "public": 1})

	def fetch_readme(self):
		frappe_app = self.get_frappe_app()
		if not frappe_app.installation:
			return
		token = get_access_token(frappe_app.installation)
		headers = {
			"Authorization": f"token {token}",
		}
		owner = frappe_app.repo_owner
		repository = frappe_app.repo
		branch = frappe_app.branch

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

		apps = frappe.db.get_all(
			"App",
			filters={"scrubbed": self.name, "public": True, "enabled": True},
			pluck="name",
		)
		groups = frappe.db.get_all(
			"Release Group",
			filters=[
				["Release Group", "enabled", "=", 1],
				["Release Group", "public", "=", 1],
				["Release Group App", "app", "in", apps],
			],
			fields=["name"],
		)
		enabled_groups = []
		for group in groups:
			group_doc = frappe.get_doc("Release Group", group.name)
			frappe_app = frappe.get_all(
				"App",
				fields=["name", "scrubbed", "branch", "url"],
				filters={"name": ("in", [row.app for row in group_doc.apps]), "frappe": True},
				limit=1,
			)[0]
			group["frappe"] = frappe_app
			enabled_groups.append(group)

		context.supported_versions = enabled_groups
