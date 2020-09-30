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
	def before_insert(self):
		self.long_description = self.fetch_readme()

	def set_route(self):
		self.route = "marketplace/apps/" + cleanup_page_name(self.title)

	def validate(self):
		self.published = self.status == "Published"

	def on_update(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save or doc_before_save.status != self.status:
			frappe_app = frappe.get_doc("Frappe App", self.frappe_app)
			frappe_app.public = self.status == "Published"
			frappe_app.save()

	def fetch_readme(self):
		frappe_app = frappe.get_doc("Frappe App", self.frappe_app)
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

		groups = frappe.get_all(
			"Release Group Frappe App",
			fields=["parent as name"],
			filters={"app": self.frappe_app},
		)
		print("groups")
		enabled_groups = []
		for group in groups:
			group_doc = frappe.get_doc("Release Group", group.name)
			if not group_doc.enabled:
				continue
			frappe_app = frappe.get_all(
				"Frappe App",
				fields=["name", "scrubbed", "branch", "url"],
				filters={"name": ("in", [row.app for row in group_doc.apps]), "frappe": True},
			)[0]
			group["frappe"] = frappe_app
			enabled_groups.append(group)

		context.supported_versions = enabled_groups
