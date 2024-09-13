# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import frappe.utils
from frappe.utils.momentjs import get_all_timezones
from press.utils import log_error
from press.utils.unique_name_generator import generate as generate_random_name


class ProductTrial(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.saas.doctype.product_trial_app.product_trial_app import ProductTrialApp
		from press.saas.doctype.product_trial_signup_field.product_trial_signup_field import (
			ProductTrialSignupField,
		)

		apps: DF.Table[ProductTrialApp]
		domain: DF.Link
		email_account: DF.Link | None
		email_full_logo: DF.AttachImage | None
		email_header_content: DF.Code
		email_subject: DF.Data
		enable_pooling: DF.Check
		logo: DF.AttachImage | None
		published: DF.Check
		release_group: DF.Link
		setup_wizard_completion_mode: DF.Literal["manual", "auto"]
		setup_wizard_payload_generator_script: DF.Code | None
		signup_fields: DF.Table[ProductTrialSignupField]
		standby_pool_size: DF.Int
		standby_queue_size: DF.Int
		title: DF.Data
		trial_days: DF.Int
		trial_plan: DF.Link
	# end: auto-generated types

	dashboard_fields = [
		"title",
		"logo",
		"description",
		"domain",
		"trial_days",
		"trial_plan",
	]

	def get_doc(self, doc):
		if not self.published:
			frappe.throw("Not permitted")

		def _parse_options(field):
			if field.fieldtype != "Select":
				return []
			if field.fieldname.endswith("_tz"):
				return get_all_timezones()
			if not field.options:
				return []
			return [option for option in ((field.options or "").split("\n")) if option]

		doc.signup_fields = [
			{
				"label": field.label,
				"fieldname": field.fieldname,
				"fieldtype": field.fieldtype,
				"options": _parse_options(field),
				"required": field.required,
			}
			for field in self.signup_fields
		]
		doc.proxy_servers = self.get_proxy_servers_for_available_clusters()
		return doc

	def validate(self):
		plan = frappe.get_doc("Site Plan", self.trial_plan)
		if plan.document_type != "Site":
			frappe.throw("Selected plan is not for site")
		if not plan.is_trial_plan:
			frappe.throw("Selected plan is not a trial plan")

	def setup_trial_site(self, team, plan, cluster=None):
		standby_site = self.get_standby_site(cluster)
		team_record = frappe.get_doc("Team", team)
		trial_end_date = frappe.utils.add_days(None, self.trial_days or 14)
		site = None
		agent_job_name = None
		if standby_site:
			site = frappe.get_doc("Site", standby_site)
			site.is_standby = False
			site.team = team_record.name
			site.trial_end_date = trial_end_date
			site.save(ignore_permissions=True)
			agent_job_name = None
			site.create_subscription(plan)
		else:
			# Create a site in the cluster, if standby site is not available
			apps = [{"app": d.app} for d in self.apps]
			is_frappe_app_present = any(d["app"] == "frappe" for d in apps)
			if not is_frappe_app_present:
				apps.insert(0, {"app": "frappe"})
			site = frappe.get_doc(
				doctype="Site",
				subdomain=self.get_unique_site_name(),
				domain=self.domain,
				group=self.release_group,
				cluster=cluster,
				is_standby=False,
				standby_for_product=self.name,
				subscription_plan=plan,
				team=team,
				apps=apps,
				trial_end_date=trial_end_date,
			)
			site.insert(ignore_permissions=True)
			agent_job_name = site.flags.get("new_site_agent_job_name", None)

		site.reload()
		site.generate_saas_communication_secret(create_agent_job=True)
		site.flags.ignore_permissions = True
		if standby_site:
			agent_job_name = site.create_user_with_team_info()
		return site, agent_job_name, bool(standby_site)

	def get_proxy_servers_for_available_clusters(self):
		clusters = self.get_available_clusters()
		proxy_servers = frappe.db.get_all(
			"Proxy Server",
			{
				"cluster": ("in", clusters),
			},
			["name", "is_primary", "cluster"],
		)
		proxy_servers_by_cluster = {}
		for proxy_server in proxy_servers:
			cluster = proxy_server.cluster
			proxy_servers_by_cluster.setdefault(cluster, []).append(proxy_server)

		proxy_servers_for_available_clusters = {}
		for cluster, proxy_servers in proxy_servers_by_cluster.items():
			primary_proxy = [d for d in proxy_servers if d.is_primary]
			if primary_proxy:
				proxy_server_name = primary_proxy[0].name
				proxy_servers_for_available_clusters[proxy_server_name] = cluster

		return proxy_servers_for_available_clusters

	def get_available_clusters(self):
		release_group = frappe.get_doc("Release Group", self.release_group)
		clusters = frappe.db.get_all(
			"Server",
			{"name": ("in", [d.server for d in release_group.servers])},
			order_by="name asc",
			pluck="Cluster",
		)
		clusters = list(set(clusters))
		public_clusters = frappe.db.get_all(
			"Cluster", {"name": ("in", clusters), "public": 1}, order_by="name asc", pluck="name"
		)
		return public_clusters

	def get_standby_site(self, cluster=None):
		filters = {
			"is_standby": True,
			"standby_for_product": self.name,
			"status": "Active",
		}
		if cluster:
			filters["cluster"] = cluster
		sites = frappe.db.get_all(
			"Site",
			filters=filters,
			pluck="name",
			order_by="creation asc",
			limit=1,
		)
		if sites:
			return sites[0]
		if cluster:
			# if site is not found and cluster was specified, try to find a site in any cluster
			return self.get_standby_site()

	def create_standby_sites_in_each_cluster(self):
		if not self.enable_pooling:
			return

		clusters = self.get_available_clusters()
		for cluster in clusters:
			self.create_standby_sites(cluster)

	def create_standby_sites(self, cluster):
		if not self.enable_pooling:
			return

		sites_to_create = self.standby_pool_size - self.get_standby_sites_count(cluster)
		if sites_to_create <= 0:
			return
		if sites_to_create > self.standby_queue_size:
			sites_to_create = self.standby_queue_size

		for i in range(sites_to_create):
			self.create_standby_site(cluster)
			frappe.db.commit()

	def create_standby_site(self, cluster):
		administrator = frappe.db.get_value("Team", {"user": "Administrator"}, "name")
		apps = [{"app": d.app} for d in self.apps]
		site = frappe.get_doc(
			doctype="Site",
			subdomain=self.get_unique_site_name(),
			domain=self.domain,
			group=self.release_group,
			cluster=cluster,
			is_standby=True,
			standby_for_product=self.name,
			team=administrator,
			apps=apps,
		)
		site.insert(ignore_permissions=True)

	def get_standby_sites_count(self, cluster):
		active_standby_sites = frappe.db.count(
			"Site",
			{
				"cluster": cluster,
				"is_standby": 1,
				"standby_for_product": self.name,
				"status": "Active",
			},
		)
		# sites that are in pending state created in the last hour
		recent_pending_standby_sites = frappe.db.count(
			"Site",
			{
				"cluster": cluster,
				"is_standby": 1,
				"standby_for_product": self.name,
				"status": ("in", ["Pending", "Installing"]),
				"creation": (">", frappe.utils.add_to_date(None, hours=-1)),
			},
		)
		return active_standby_sites + recent_pending_standby_sites

	def get_unique_site_name(self):
		subdomain = generate_random_name()
		filters = {
			"subdomain": subdomain,
			"domain": self.domain,
			"status": ("!=", "Archived"),
		}
		while frappe.db.exists("Site", filters):
			subdomain = generate_random_name()
		return subdomain


def replenish_standby_sites():
	"""Create standby sites for all products with pooling enabled. This is called by the scheduler."""
	products = frappe.get_all("Product Trial", {"enable_pooling": 1}, pluck="name")
	for product in products:
		product = frappe.get_doc("Product Trial", product)
		try:
			product.create_standby_sites_in_each_cluster()
			frappe.db.commit()
		except Exception:
			log_error("Replenish Standby Sites Error", product=product.name)
			frappe.db.rollback()
