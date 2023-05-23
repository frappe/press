# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests

from typing import Dict, List
from base64 import b64decode
from press.utils import get_last_doc
from press.api.github import get_access_token
from frappe.query_builder.functions import Cast_
from frappe.website.utils import cleanup_page_name
from frappe.website.website_generator import WebsiteGenerator
from press.marketplace.doctype.marketplace_app_plan.marketplace_app_plan import (
	get_app_plan_features,
)
from press.press.doctype.marketplace_app.utils import get_rating_percentage_distribution
from frappe.utils.safe_exec import safe_exec


class MarketplaceApp(WebsiteGenerator):
	def autoname(self):
		self.name = self.app

	def before_insert(self):
		if not frappe.flags.in_test:
			self.long_description = self.fetch_readme()

		self.set_route()

	def set_route(self):
		self.route = "marketplace/apps/" + cleanup_page_name(self.app)

	def validate(self):
		self.published = self.status == "Published"
		self.validate_sources()
		self.validate_number_of_screenshots()

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

	def change_branch(self, source, version, to_branch):
		existing_source = frappe.db.exists(
			"App Source",
			{
				"name": ("!=", self.name),
				"app": self.app,
				"repository_url": frappe.db.get_value(
					"App Source", {"name": source}, "repository_url"
				),
				"branch": to_branch,
				"team": self.team,
			},
		)
		if existing_source:
			# If source with branch to switch already exists, just add version to child table of source and use the same
			try:
				source_doc = frappe.get_doc("App Source", existing_source)
				source_doc.append("versions", {"version": version})
				source_doc.save()
			except Exception:
				pass

			for source in self.sources:
				if source.source == source:
					source.source = existing_source
					self.save()
		else:
			# if a different source with the branch to switch doesn't exists update the existing source
			source_doc = frappe.get_doc("App Source", source)
			source_doc.branch = to_branch
			source_doc.save()

	def add_version(self, version, branch):
		existing_source = frappe.db.exists(
			"App Source",
			[
				["App Source", "app", "=", self.app],
				["App Source", "team", "=", self.team],
				["App Source", "branch", "=", branch],
			],
		)
		if existing_source:
			# If source with branch to switch already exists, just add version to child table of source and use the same
			source_doc = frappe.get_doc("App Source", existing_source)
			try:
				source_doc.append("versions", {"version": version})
				source_doc.save()
			except Exception:
				pass
		else:
			# create new app source for version and branch to switch
			source_doc = frappe.get_doc(
				{
					"doctype": "App Source",
					"app": self.app,
					"team": self.team,
					"branch": branch,
					"repository_url": frappe.db.get_value(
						"App Source", {"name": self.sources[0].source}, "repository_url"
					),
					"public": 1,
				}
			)
			source_doc.append("versions", {"version": version})
			source_doc.insert(ignore_permissions=True)

		self.append("sources", {"version": version, "source": source_doc.name})
		self.save()

	def remove_version(self, version):
		if self.status == "Published" and len(self.sources) == 1:
			frappe.throw("Failed to remove. Need at least 1 version for a published app")

		for i, source in enumerate(self.sources):
			if source.version == version:
				# remove from marketplace app source child table
				self.sources.pop(i)
				self.save()

				app_source = frappe.get_cached_doc("App Source", source.source)
				for j, source_version in enumerate(app_source.versions):
					if source_version.version == version and len(app_source.versions) > 1:
						# remove from app source versions child table
						app_source.versions.pop(j)
						app_source.save()
						break
				break

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
		context.plans = self.get_plans()

		user_reviews = self.get_user_reviews()
		ratings_summary = self.get_user_ratings_summary(user_reviews)

		context.user_reviews = user_reviews
		context.ratings_summary = ratings_summary

	def get_user_reviews(self) -> List:
		app_user_review = frappe.qb.DocType("App User Review")
		user = frappe.qb.DocType("User")

		query = (
			frappe.qb.from_(app_user_review)
			.join(user)
			.on(user.name == app_user_review.reviewer)
			.select(
				app_user_review.title,
				Cast_(5 * app_user_review.rating, "INT").as_("rating"),
				app_user_review.review,
				app_user_review.creation,
				app_user_review.reviewer,
				user.full_name.as_("user_name"),
			)
			.where(app_user_review.app == self.name)
		)
		return query.run(as_dict=True)

	def get_user_ratings_summary(self, reviews: List) -> Dict:
		total_num_reviews = len(reviews)
		avg_rating = 0.0

		if len(reviews) > 0:
			avg_rating = sum([r.rating for r in reviews]) / len(reviews)
			avg_rating = frappe.utils.rounded(avg_rating, 1)

		rating_percentages = get_rating_percentage_distribution(reviews)

		return {
			"total_num_reviews": total_num_reviews,
			"avg_rating": avg_rating,
			"rating_percentages": rating_percentages,
		}

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

	def total_installs(self):
		return frappe.db.count("Site App", filters={"app": self.app})

	def total_active_sites(self):
		return frappe.db.sql(
			"""
			SELECT
				count(*)
			FROM
				tabSite site
			LEFT JOIN
				`tabSite App` app
			ON
				app.parent = site.name
			WHERE
				site.status = "Active" AND app.app = %s
		""",
			(self.app,),
		)[0][0]

	def total_active_benches(self):
		return frappe.db.sql(
			"""
			SELECT
				count(*)
			FROM
				tabBench bench
			LEFT JOIN
				`tabBench App` app
			ON
				app.parent = bench.name
			WHERE
				bench.status = "Active" AND app.app = %s
		""",
			(self.app,),
		)[0][0]

	def get_analytics(self):
		return {
			"total_installs": self.total_installs(),
			"num_installs_active_sites": self.total_active_sites(),
			"num_installs_active_benches": self.total_active_benches(),
		}

	def get_plans(self, frappe_version: str = None) -> List:
		return get_plans_for_app(self.name, frappe_version)


def get_plans_for_app(
	app_name, frappe_version=None, include_free=True, include_disabled=False
):  # Unused for now, might use later
	from press.press.doctype.team.team import is_us_eu

	plans = []
	filters = {"app": app_name}

	if not include_free:
		filters["is_free"] = False

	if not include_disabled:
		filters["enabled"] = True

	filters["us_eu"] = (
		frappe.db.get_value("Saas Settings", app_name, "multiplier_pricing") and is_us_eu()
	)

	marketplace_app_plans = frappe.get_all(
		"Marketplace App Plan",
		filters=filters,
		fields=[
			"name",
			"plan",
			"discount_percent",
			"gst",
			"marked_most_popular",
			"is_free",
			"enabled",
			"block_monthly",
		],
	)

	for app_plan in marketplace_app_plans:
		plan_data = {}
		plan_data.update(app_plan)

		plan_discount_percent = app_plan.discount_percent
		plan_data["discounted"] = plan_discount_percent > 0
		plan_prices = frappe.db.get_value(
			"Plan", app_plan.plan, ["plan_title", "price_usd", "price_inr"], as_dict=True
		)

		plan_data.update(plan_prices)
		plan_data["features"] = get_app_plan_features(app_plan.name)

		plans.append(plan_data)

	plans.sort(key=lambda x: x["price_usd"])
	plans.sort(key=lambda x: x["enabled"], reverse=True)  # Enabled Plans First

	return plans


def marketplace_app_hook(app=None, site="", op="install"):
	if app is None:
		site_apps = frappe.get_all("Site App", filters={"parent": site}, pluck="app")
		for app in site_apps:
			run_script(app, site, op)
	else:
		run_script(app, site, op)


def get_script_name(app, op):
	if op == "install" and frappe.db.get_value(
		"Marketplace App", app, "run_after_install_script"
	):
		return "after_install_script"

	elif op == "uninstall" and frappe.db.get_value(
		"Marketplace App", app, "run_after_uninstall_script"
	):
		return "after_uninstall_script"
	else:
		return ""


def run_script(app, site, op):
	script = get_script_name(app, op)
	if script:
		script = frappe.db.get_value("Marketplace App", app, script)
		local = {"doc": frappe.get_doc("Site", site)}
		safe_exec(script, _locals=local)
