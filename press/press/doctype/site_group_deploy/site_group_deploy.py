# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class SiteGroupDeploy(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.site_group_deploy_app.site_group_deploy_app import (
			SiteGroupDeployApp,
		)

		apps: DF.Table[SiteGroupDeployApp]
		bench: DF.Link | None
		cluster: DF.Link
		release_group: DF.Link | None
		site: DF.Link | None
		status: DF.Literal[
			"Pending",
			"Deploying Bench",
			"Bench Deployed",
			"Bench Deploy Failed",
			"Creating Site",
			"Site Created",
			"Site Creation Failed",
		]
		subdomain: DF.Data
		team: DF.Link
		version: DF.Link | None
	# end: auto-generated types

	dashboard_fields = ("status", "site", "release_group")

	def before_insert(self):
		self.set_latest_version()
		self.check_if_rg_or_site_exists()

	def after_insert(self):
		if self.release_group:
			return

		group = self.create_release_group()

		self.status = "Deploying Bench"
		self.save()

		group.initial_deploy()

	def set_latest_version(self):
		if self.version:
			return

		self.version = frappe.db.get_value("Frappe Version", {"status": "stable"}, order_by="number desc")

	def check_if_rg_or_site_exists(self):
		from press.press.doctype.site.site import Site

		if frappe.db.exists("Release Group", {"title": self.subdomain}):
			frappe.throw(f"Release Group with title {self.subdomain} already exists")

		domain = frappe.db.get_single_value("Press Settings", "domain")
		if Site.exists(self.subdomain, domain):
			frappe.throw(f"Site with subdomain {self.subdomain} already exists")

	def create_release_group(self):
		from press.press.doctype.release_group.release_group import new_release_group

		apps = [{"app": app.app, "source": app.source} for app in self.apps]

		group = new_release_group(
			title=self.subdomain,
			version=self.version,
			apps=apps,
			team=self.team,
			cluster=self.cluster,
		)

		self.release_group = group.name
		self.save()

		return group

	def create_site(self):
		cheapest_private_bench_plan = frappe.db.get_value(
			"Site Plan",
			{
				"private_benches": 1,
				"document_type": "Site",
				"price_inr": ["!=", 0],
				"price_usd": ["!=", 0],
			},
			order_by="price_inr asc",
		)

		apps = [{"app": app.app} for app in self.apps]
		app_plan_map = {app.app: {"name": app.plan} for app in self.apps if app.plan}

		try:
			site = frappe.get_doc(
				{
					"doctype": "Site",
					"team": self.team,
					"subdomain": self.subdomain,
					"apps": apps,
					"cluster": self.cluster,
					"release_group": self.release_group,
					"bench": self.bench,
					"domain": frappe.db.get_single_value("Press Settings", "domain"),
					"subscription_plan": cheapest_private_bench_plan,
					"app_plans": app_plan_map,
				}
			).insert()

			self.site = site.name
			self.status = "Creating Site"

		except frappe.exceptions.ValidationError:
			self.status = "Site Creation Failed"

		self.save()

	def update_site_group_deploy_on_deploy_failure(self, deploy):
		if deploy and deploy.status == "Failure":
			self.status = "Bench Deploy Failed"
			self.save()

	def update_site_group_deploy_on_process_job(self, job):
		if job.job_type == "New Bench":
			if job.status == "Success":
				self.bench = job.bench
				self.status = "Bench Deployed"
				self.save()
				self.create_site()

			elif job.status == "Failure":
				self.status = "Bench Deploy Failed"
				self.save()

		elif job.job_type == "New Site":
			if job.status == "Success":
				self.status = "Site Created"
				self.save()
			elif job.status == "Failure":
				self.status = "Site Creation Failed"
				self.save()
