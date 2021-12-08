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
		self.validate_number_of_screenshots()
		self.validate_plans()

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

	def validate_number_of_screenshots(self):
		max_allowed_screenshots = frappe.db.get_single_value(
			"Press Settings", "max_allowed_screenshots"
		)
		if len(self.screenshots) > max_allowed_screenshots:
			frappe.throw(
				f"You cannot add more than {max_allowed_screenshots} screenshots for an app."
			)

	def validate_plans(self):
		for plan in self.available_plans:
			plan_for_doctype = frappe.db.get_value("Plan", plan.plan, "document_type")
			if plan_for_doctype != "Marketplace App":
				frappe.throw(f"Plan {frappe.bold(plan.plan)} is not a marketplace app plan!")

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

		supported_versions = []
		public_rgs = frappe.get_all(
			"Release Group", filters={"public": True}, fields=["version", "name"]
		)

		unique_public_rgs = {}
		for rg in public_rgs:
			if rg.version not in unique_public_rgs:
				unique_public_rgs[rg.version] = rg.name

		for source in self.sources:
			if source.version not in unique_public_rgs:
				continue

			frappe_source_name = frappe.get_doc(
				"Release Group App", {"app": "frappe", "parent": unique_public_rgs[source.version]}
			).source
			frappe_source = frappe.db.get_value(
				"App Source", frappe_source_name, ["repository_url", "branch"], as_dict=True
			)

			app_source = frappe.db.get_value(
				"App Source", source.source, ["repository_url", "branch", "public"], as_dict=True
			)

			supported_versions.append(
				frappe._dict(
					{
						"version": source.version,
						"app_source": app_source,
						"frappe_source": frappe_source,
					}
				)
			)

		# Sort based on version
		supported_versions.sort(key=lambda x: x.version, reverse=True)

		context.supported_versions = supported_versions

		# Add publisher info
		publisher_profile = frappe.get_all(
			"Marketplace Publisher Profile",
			filters={"team": self.team},
			fields=["display_name", "contact_email"],
			limit=1,
		)

		if publisher_profile:
			context.publisher_profile = publisher_profile[0]

		context.no_of_installs = self.get_analytics().get("total_installs")

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

	def get_analytics(self):
		app_name = self.app
		site_names = frappe.get_all("Site App", filters={"app": app_name}, pluck="parent")

		total_installs = len(site_names)
		num_installs_active_sites = (
			frappe.db.count("Site", filters={"name": ("in", site_names), "status": "Active"})
			if site_names
			else 0
		)

		bench_names = frappe.get_all("Bench App", filters={"app": app_name}, pluck="parent")
		num_installs_active_benches = (
			frappe.db.count("Bench", filters={"name": ("in", bench_names), "status": "Active"})
			if bench_names
			else 0
		)

		return {
			"total_installs": total_installs,
			"num_installs_active_sites": num_installs_active_sites,
			"num_installs_active_benches": num_installs_active_benches,
		}
