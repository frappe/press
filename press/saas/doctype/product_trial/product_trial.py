# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.utils.data import get_url
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
		create_additional_system_user: DF.Check
		domain: DF.Link
		email_account: DF.Link | None
		email_full_logo: DF.AttachImage | None
		email_header_content: DF.Code
		email_subject: DF.Data
		enable_pooling: DF.Check
		logo: DF.AttachImage | None
		published: DF.Check
		redirect_to_after_login: DF.Data
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

	dashboard_fields = (
		"title",
		"logo",
		"domain",
		"trial_days",
		"trial_plan",
		"redirect_to_after_login",
	)

	USER_LOGIN_PASSWORD_FIELD = "user_login_password"

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
		doc.prefilled_site_label = self.get_prefilled_site_label()
		return doc

	def validate(self):
		plan = frappe.get_doc("Site Plan", self.trial_plan)
		if plan.document_type != "Site":
			frappe.throw("Selected plan is not for site")
		if not plan.is_trial_plan:
			frappe.throw("Selected plan is not a trial plan")

		for field in self.signup_fields:
			if field.fieldname == self.USER_LOGIN_PASSWORD_FIELD:
				if not field.required:
					frappe.throw(f"{self.USER_LOGIN_PASSWORD_FIELD} field should be marked as required")
				if field.fieldtype != "Password":
					frappe.throw(f"{self.USER_LOGIN_PASSWORD_FIELD} field should be of type Password")

		if not self.redirect_to_after_login.startswith("/"):
			frappe.throw("Redirection route after login should start with /")

	def setup_trial_site(self, site_label, team, cluster=None, account_request=None):
		from press.press.doctype.site.site import get_plan_config

		standby_site = self.get_standby_site(cluster)
		trial_end_date = frappe.utils.add_days(None, self.trial_days or 14)
		site = None
		agent_job_name = None
		apps_site_config = get_app_subscriptions_site_config([d.app for d in self.apps])
		plan = self.trial_plan

		if frappe.db.exists("Site", {"site_label": site_label, "status": ("!=", "Archived")}):
			frappe.throw(f"Site with label {site_label} already exists")

		if standby_site:
			site = frappe.get_doc("Site", standby_site)
			site.is_standby = False
			site.team = team
			site.trial_end_date = trial_end_date
			site.account_request = account_request
			site._update_configuration(apps_site_config, save=False)
			site._update_configuration(get_plan_config(plan), save=False)
			site.site_label = site_label
			site.save(ignore_permissions=True)
			site.create_subscription(plan)
			site.reload()
			site.generate_saas_communication_secret(create_agent_job=True, save=True)
			if self.create_additional_system_user:
				agent_job_name = site.create_user_with_team_info()
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
				account_request=account_request,
				is_standby=False,
				standby_for_product=self.name,
				subscription_plan=plan,
				team=team,
				apps=apps,
				trial_end_date=trial_end_date,
				site_label=site_label,
			)
			site._update_configuration(apps_site_config, save=False)
			site._update_configuration(get_plan_config(plan), save=False)
			site.generate_saas_communication_secret(create_agent_job=False, save=False)
			if self.setup_wizard_completion_mode == "auto" or not self.create_additional_system_user:
				site.flags.ignore_additional_system_user_creation = True
			site.insert(ignore_permissions=True)
			agent_job_name = site.flags.get("new_site_agent_job_name", None)

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
		return frappe.db.get_all(
			"Cluster", {"name": ("in", clusters), "public": 1}, order_by="name asc", pluck="name"
		)

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
		return None

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

		for _i in range(sites_to_create):
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
		subdomain = f"{self.name}-{generate_random_name(segment_length=3, num_segments=2)}"
		filters = {
			"subdomain": subdomain,
			"domain": self.domain,
			"status": ("!=", "Archived"),
		}
		while frappe.db.exists("Site", filters):
			subdomain = f"{self.name}-{generate_random_name(segment_length=3, num_segments=2)}"
		return subdomain

	def get_prefilled_site_label(self):
		def get_site_label(count=1):
			user_first_name = frappe.db.get_value("User", frappe.session.user, "first_name")
			site_label = f"{user_first_name}'s {self.title} Site"
			if count > 1:
				site_label = f"{site_label} {count}"
			if frappe.db.exists("Site", {"site_label": site_label}):
				return get_site_label(count + 1)
			return site_label

		return get_site_label()


def get_app_subscriptions_site_config(apps: list[str]):
	subscriptions = []
	site_config = {}

	for app in apps:
		free_plan = frappe.get_all(
			"Marketplace App Plan",
			{"enabled": 1, "price_usd": ("<=", 0), "app": app},
			pluck="name",
		)
		if free_plan:
			new_subscription = frappe.get_doc(
				{
					"doctype": "Subscription",
					"document_type": "Marketplace App",
					"document_name": app,
					"plan_type": "Marketplace App Plan",
					"plan": free_plan[0],
					"enabled": 0,
					"team": frappe.get_value("Team", {"user": "Administrator"}, "name"),
				}
			).insert(ignore_permissions=True)

			subscriptions.append(new_subscription)
			config = frappe.db.get_value("Marketplace App", app, "site_config")
			config = json.loads(config) if config else {}
			site_config.update(config)

	for s in subscriptions:
		site_config.update({"sk_" + s.document_name: s.secret_key})

	return site_config


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


def send_verification_mail_for_login(email: str, product: str, code: str):
	"""Send verification mail for login."""
	if frappe.conf.developer_mode:
		print(f"\nVerification Code for {product}:")
		print(f"Email : {email}")
		print(f"Code : {code}")
		print()
		return
	product_trial: ProductTrial = frappe.get_doc("Product Trial", product)
	sender = ""
	subject = f"{code} - Verification Code for {product_trial.title} Login"
	args = {
		"header_content": f"<p>You have requested a verification code to login to your {product_trial.title} site. The code is valid for 5 minutes.</p>",
		"otp": code,
	}
	if product_trial.email_full_logo:
		args.update({"image_path": get_url(product_trial.email_full_logo, True)})
	if product_trial.email_account:
		sender = frappe.get_value("Email Account", product_trial.email_account, "email_id")

	frappe.sendmail(
		sender=sender,
		recipients=email,
		subject=subject,
		template="product_trial_verify_account",
		args=args,
		now=True,
	)


def sync_product_site_users():
	"""Fetch and sync users from product sites, so that they can be used for login to the site from FC."""

	product_groups = frappe.db.get_all(
		"Product Trial", {"published": 1}, ["release_group"], pluck="release_group"
	)
	product_benches = frappe.get_all(
		"Bench", {"group": ("in", product_groups), "status": "Active"}, pluck="name"
	)
	# print(f"Syncing users for {product_benches}")
	# _sync_product_site_users(product_benches)
	frappe.enqueue(
		"press.saas.doctype.product_trial.product_trial._sync_product_site_users",
		queue="short",
		product_benches=product_benches,
		job_id="sync_product_site_users",
		deduplicate=True,
		enqueue_after_commit=True,
	)
	frappe.db.commit()


def _sync_product_site_users(product_benches):
	for bench_name in product_benches:
		bench = frappe.get_doc("Bench", bench_name)
		# Skip syncing analytics for benches that have been archived (after the job was enqueued)
		if bench.status != "Active":
			return
		try:
			bench.sync_product_site_users()
			frappe.db.commit()
		except Exception:
			log_error(
				"Bench Analytics Sync Error",
				bench=bench.name,
				reference_doctype="Bench",
				reference_name=bench.name,
			)
			frappe.db.rollback()
