# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.utils.data import get_url

from press.utils import log_error, validate_subdomain
from press.utils.unique_name_generator import generate as generate_random_name


class ProductTrial(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.saas.doctype.product_trial_app.product_trial_app import ProductTrialApp

		apps: DF.Table[ProductTrialApp]
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
		standby_pool_size: DF.Int
		standby_queue_size: DF.Int
		suspension_email_content: DF.HTMLEditor | None
		suspension_email_subject: DF.Data | None
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

	def get_doc(self, doc):
		if not self.published:
			frappe.throw("Not permitted")

		doc.proxy_servers = self.get_proxy_servers_for_available_clusters()
		return doc

	def validate(self):
		plan = frappe.get_doc("Site Plan", self.trial_plan)
		if plan.document_type != "Site":
			frappe.throw("Selected plan is not for site")
		if not plan.is_trial_plan:
			frappe.throw("Selected plan is not a trial plan")

		if not self.redirect_to_after_login.startswith("/"):
			frappe.throw("Redirection route after login should start with /")

	def setup_trial_site(self, subdomain, team, cluster=None, account_request=None):
		from press.press.doctype.site.site import Site, get_plan_config

		validate_subdomain(subdomain)
		Site.exists(subdomain, self.domain)

		site_domain = f"{subdomain}.{self.domain}"

		standby_site = self.get_standby_site(cluster)

		trial_end_date = frappe.utils.add_days(None, self.trial_days or 14)
		site = None
		agent_job_name = None
		plan = self.trial_plan

		if standby_site:
			site = frappe.get_doc("Site", standby_site)
			site.is_standby = False
			site.team = team
			site.trial_end_date = trial_end_date
			site.account_request = account_request
			apps_site_config = get_app_subscriptions_site_config([d.app for d in self.apps], standby_site)
			site._update_configuration(apps_site_config, save=False)
			site._update_configuration(get_plan_config(plan), save=False)
			site.signup_time = frappe.utils.now()
			site.generate_saas_communication_secret(create_agent_job=True, save=False)
			site.save()  # Save is needed for create_subscription to work TODO: remove this
			site.create_subscription(plan)
			site.reload()
			self.set_site_domain(site, site_domain)
		else:
			# Create a site in the cluster, if standby site is not available
			apps = [{"app": d.app} for d in self.apps]
			is_frappe_app_present = any(d["app"] == "frappe" for d in apps)
			if not is_frappe_app_present:
				apps.insert(0, {"app": "frappe"})

			site = frappe.get_doc(
				doctype="Site",
				subdomain=subdomain,
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
				signup_time=frappe.utils.now(),
			)
			apps_site_config = get_app_subscriptions_site_config([d.app for d in self.apps], site.name)
			site._update_configuration(apps_site_config, save=False)
			site._update_configuration(get_plan_config(plan), save=False)
			site.generate_saas_communication_secret(create_agent_job=False, save=False)
			site.insert()
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

	def set_site_domain(self, site: Site, site_domain: str):
		if not site_domain:
			return

		if site.name == site_domain or site.host_name == site_domain:
			return

		site.add_domain_for_product_site(site_domain)
		site.add_domain_to_config(site_domain)

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
		server = self.get_server_from_cluster(cluster)
		site = frappe.get_doc(
			doctype="Site",
			subdomain=self.get_unique_site_name(),
			domain=self.domain,
			group=self.release_group,
			cluster=cluster,
			server=server,
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
		# sites that are created in the last hour
		recent_standby_sites = frappe.db.count(
			"Site",
			{
				"cluster": cluster,
				"is_standby": 1,
				"standby_for_product": self.name,
				"status": ("not in", ["Archived", "Suspended"]),
				"creation": (">", frappe.utils.add_to_date(None, hours=-1)),
			},
		)
		return active_standby_sites + recent_standby_sites

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

	def get_server_from_cluster(self, cluster):
		"""Return the server with the least number of standby sites in the cluster"""

		ReleaseGroupServer = frappe.qb.DocType("Release Group Server")
		Server = frappe.qb.DocType("Server")

		servers = (
			frappe.qb.from_(ReleaseGroupServer)
			.select(ReleaseGroupServer.server)
			.where(ReleaseGroupServer.parent == self.release_group)
			.join(Server)
			.on(Server.name == ReleaseGroupServer.server)
			.where(Server.cluster == cluster)
			.run(pluck="server")
		)

		server_sites = {}
		for server in servers:
			server_sites[server] = frappe.db.count(
				"Site",
				{
					"server": server,
					"status": ("!=", "Archived"),
					"is_standby": 1,
				},
			)

		# get the server with the least number of sites
		return min(server_sites, key=server_sites.get)


def get_app_subscriptions_site_config(apps: list[str], site: str | None = None) -> dict:
	from press.utils import get_current_team

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
					"site": site,
					"enabled": 1,
					"team": get_current_team(),
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
		except Exception as e:
			log_error(
				"Replenish Standby Sites Error",
				data=e,
				reference_doctype="Product Trial",
				reference_name=product.name,
			)
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


def send_suspend_mail(site: str, product: str) -> None:
	"""Send suspension mail to the site owner."""

	site = frappe.db.get_value("Site", site, ["team", "trial_end_date", "name", "host_name"], as_dict=True)
	product = frappe.db.get_value(
		"Product Trial",
		product,
		["title", "suspension_email_subject", "suspension_email_content", "email_full_logo", "logo"],
		as_dict=True,
	)

	if not site or not product:
		return

	sender = ""
	subject = (
		product.suspension_email_subject.format(product_title=product.title)
		or f"Your {product.title} site is expired"
	)
	recipient = frappe.get_value("Team", site.team, "user")
	args = {}

	# TODO: enable it when we use the full logo
	# if product.email_full_logo:
	# 	args.update({"image_path": get_url(product.email_full_logo, True)})
	if product.logo:
		args.update({"logo": get_url(product.logo, True), "title": product.title})
	if product.email_account:
		sender = frappe.get_value("Email Account", product.email_account, "email_id")

	context = {
		"site": site,
		"product": product,
	}
	message = frappe.render_template(product.suspension_email_content, context)
	args.update({"message": message})

	frappe.sendmail(
		sender=sender,
		recipients=recipient,
		subject=subject,
		template="product_trial_email",
		args=args,
	)
