# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests

from base64 import b64decode
from press.utils import get_last_doc
from press.api.github import get_access_token
from frappe.website.utils import cleanup_page_name
from frappe.website.website_generator import WebsiteGenerator


class MarketplaceApp(WebsiteGenerator):
	def autoname(self):
		self.name = self.app

	def before_insert(self):
		self.long_description = self.fetch_readme()
		self.set_route()

	def set_route(self):
		self.route = "marketplace/apps/" + cleanup_page_name(self.app)

	def validate(self):
		self.published = self.status == "Published"
		self.validate_sources()

	def validate_sources(self):
		for source in self.sources:
			app_source = frappe.get_doc("App Source", source.source)

			if app_source.app != self.app:
				frappe.throw(
					f"App Source {frappe.bold(source.source)} does not belong to this app!"
				)

			app_source_versions = [v.version for v in app_source.versions]
			if source.version not in app_source_versions:
				frappe.throw(
					f"App Source {frappe.bold(source.source)} does not contain"
					f" version: {frappe.bold(source.version)}"
				)

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

	def get_deploy_information(self):
		"""Return the deploy information this marketplace app"""
		# Public Release Groups, Benches
		# Is on release group, but not on bench -> awaiting deploy
		deploy_info = {}

		for source in self.sources:
			version = source.version
			deploy_info[version] = "Not Deployed"

			release_groups = frappe.get_all(
				"Release Group", filters={"public": 1, "version": version}, pluck="name"
			)

			for rg_name in release_groups:
				release_group = frappe.get_doc("Release Group", rg_name)
				sources_on_rg = [a.source for a in release_group.apps]

				latest_active_bench = get_last_doc(
					"Bench", filters={"status": "Active", "group": rg_name}
				)

				if latest_active_bench:
					sources_on_bench = [a.source for a in latest_active_bench.apps]
					if source.source in sources_on_bench:
						# Is deployed on a bench
						deploy_info[version] = "Deployed"

				if (source.source in sources_on_rg) and (deploy_info[version] != "Deployed"):
					# Added to release group, but not yet deployed to a bench
					deploy_info[version] = "Awaiting Deploy"

		return deploy_info
