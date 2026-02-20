# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import Any

import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.utils.data import get_url

from press.utils import log_error
from press.utils.jobs import has_job_timeout_exceeded
from press.utils.unique_name_generator import generate as generate_random_name


class ProductTrial(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.site.site import Site
		from press.saas.doctype.hybrid_pool_item.hybrid_pool_item import HybridPoolItem
		from press.saas.doctype.product_trial_app.product_trial_app import ProductTrialApp

		apps: DF.Table[ProductTrialApp]
		domain: DF.Link
		email_account: DF.Link | None
		email_full_logo: DF.AttachImage | None
		email_header_content: DF.Code
		email_subject: DF.Data
		enable_hybrid_pooling: DF.Check
		enable_pooling: DF.Check
		hybrid_pool_rules: DF.Table[HybridPoolItem]
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

		self.validate_hybrid_rules()

	def validate_hybrid_rules(self):
		for rule in self.hybrid_pool_rules:
			if not frappe.db.exists("Release Group App", {"parent": self.release_group, "app": rule.app}):
				frappe.throw(
					f"App {rule.app} is not present in release group {self.release_group}. "
					"Please add the app to the release group."
				)

	def setup_trial_site(
		self,
		subdomain: str,
		domain: str,
		team: str,
		cluster: str | None = None,
		account_request: str | None = None,
	):
		from press.press.doctype.site.site import Site, get_plan_config

		if Site.exists(subdomain, domain):
			frappe.throw("Site with this subdomain already exists")

		site_domain = f"{subdomain}.{domain}"

		standby_site = self.get_standby_site(cluster, account_request)

		trial_end_date = frappe.utils.add_days(None, self.trial_days or 14)
		agent_job_name: str | None = None
		plan = self.trial_plan

		if standby_site:
			site: Site = frappe.get_doc("Site", standby_site)
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
			site.reload()
			self.set_site_domain(site, site_domain)
		else:
			# Create a site in the cluster, if standby site is not available
			apps = self.get_site_apps(account_request)
			is_frappe_app_present = any(d["app"] == "frappe" for d in apps)
			if not is_frappe_app_present:
				apps.insert(0, {"app": "frappe"})

			site = frappe.get_doc(
				doctype="Site",
				subdomain=subdomain,
				domain=domain,
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

	def get_site_apps(self, account_request: str | None = None):
		"""Get the list of site apps to include in the site creation
		Also includes hybrid apps if account request has relevant fields
		"""
		apps = [{"app": d.app} for d in self.apps]

		if account_request and self.enable_hybrid_pooling:
			fields = [rule.field for rule in self.hybrid_pool_rules]
			acc_req = (
				frappe.db.get_value(
					"Account Request",
					account_request,
					fields,
					as_dict=True,
				)
				if account_request
				else None
			)

			for rule in self.hybrid_pool_rules:
				value = acc_req.get(rule.field) if acc_req else None
				if not value:
					break

				if rule.value == value:
					apps += [{"app": rule.app}]
					break

		return apps

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

	@staticmethod
	def get_preferred_site(filters) -> str | None:
		sites = frappe.db.get_all(
			"Site",
			filters=filters,
			pluck="name",
			order_by="status,standby_for,creation asc",
			limit=10,
		)
		if not sites:
			return None
		Site = frappe.qb.DocType("Site")
		Incident = frappe.qb.DocType("Incident")
		sites_without_incident = (
			frappe.qb.from_(Site)
			.select(Site.name)
			.left_join(Incident)
			.on(
				(Site.server == Incident.server)
				& (Incident.status.isin(["Confirmed", "Validating", "Acknowledged"]))
			)
			.where(Site.name.isin(sites))
			.where(Incident.name.isnull())
			.run(as_dict=True)
		)
		sites_without_incident = [site["name"] for site in sites_without_incident]
		return sites_without_incident[0] if sites_without_incident else sites[0]

	def get_standby_site(self, cluster: str | None = None, account_request: str | None = None) -> str | None:
		filters = {
			"is_standby": True,
			"standby_for_product": self.name,
			"status": "Active",
		}
		if cluster:
			filters["cluster"] = cluster

		fields = [rule.field for rule in self.hybrid_pool_rules]
		acc_req = (
			frappe.db.get_value(
				"Account Request",
				account_request,
				fields,
				as_dict=True,
			)
			if account_request
			else None
		)
		for rule in self.hybrid_pool_rules:
			value = acc_req.get(rule.field) if acc_req else None
			if not value:
				break

			if rule.value == value:
				filters["hybrid_for"] = rule.app
				break

		return ProductTrial.get_preferred_site(filters)

	def create_standby_sites_in_each_cluster(self):
		if not self.enable_pooling:
			return

		clusters = self.get_available_clusters()
		for cluster in clusters:
			try:
				self.create_standby_sites(cluster)
				frappe.db.commit()
			except Exception as e:
				log_error(
					"Unable to Create Standby Sites",
					data=e,
					reference_doctype="Product Trial",
					reference_name=self.name,
				)
				frappe.db.rollback()

	def create_standby_sites(self, cluster):
		if not self.enable_pooling:
			return

		self._create_standby_sites(cluster)

		if self.enable_hybrid_pooling:
			for rule in self.hybrid_pool_rules:
				self._create_standby_sites(cluster, rule)

	def _create_standby_sites(self, cluster: str, rule: HybridPoolItem | None = None):
		if rule and rule.preferred_cluster and rule.preferred_cluster != cluster:
			return

		standby_pool_size = rule.custom_pool_size if rule else self.standby_pool_size
		sites_to_create = standby_pool_size - self.get_standby_sites_count(
			cluster, rule.app if rule else None
		)
		if sites_to_create <= 0:
			return
		if sites_to_create > self.standby_queue_size:
			sites_to_create = self.standby_queue_size

		for _i in range(sites_to_create):
			self.create_standby_site(cluster, rule)
			frappe.db.commit()

	def create_standby_site(self, cluster: str, rule: HybridPoolItem | None = None):
		from frappe.core.utils import find

		administrator = frappe.db.get_value("Team", {"user": "Administrator"}, "name")
		apps = [{"app": d.app} for d in self.apps]

		if rule:
			apps += [{"app": rule.app}]

		server = self.get_server_from_cluster(cluster)
		cluster_domains = frappe.db.get_all(
			"Root Domain", {"name": ("like", f"%.{self.domain}")}, ["name", "default_cluster as cluster"]
		)
		cluster_domain = find(
			cluster_domains,
			lambda d: d.cluster == cluster if cluster else False,
		)
		domain = cluster_domain.name if cluster_domain else self.domain
		site = frappe.get_doc(
			doctype="Site",
			subdomain=self.get_unique_site_name(),
			domain=domain,
			group=self.release_group,
			cluster=cluster,
			server=server,
			is_standby=True,
			standby_for_product=self.name,
			hybrid_for=rule.app if rule else None,
			team=administrator,
			apps=apps,
		)
		site.insert(ignore_permissions=True)

	def get_standby_sites_count(self, cluster: str, hybrid_for: str | None = None):
		one_hour_ago = frappe.utils.add_to_date(None, hours=-1)
		Site = frappe.qb.DocType("Site")
		query = (
			frappe.qb.from_(Site)
			.select(Site.name)
			.distinct()
			.where(
				(Site.cluster == cluster) & (Site.is_standby == 1) & (Site.standby_for_product == self.name)
			)
		)

		if hybrid_for is None:
			query = query.where(Site.hybrid_for.isnull())
		else:
			query = query.where(Site.hybrid_for == hybrid_for)

		query = query.where(
			(Site.status == "Active")
			| ((Site.creation > one_hour_ago) & (Site.status.notin(["Archived", "Suspended"])))
		)
		standby_sites = query.run(pluck=True)
		return len(standby_sites)

	def get_prefilled_subdomain(self, account_request: str | None = None) -> str:
		"""
		Get the prefilled subdomain based on the email domain of the account request.
		If the email domain belongs to a free email provider, generate a unique site name instead.
		"""
		if not account_request:
			return self.get_unique_site_name()

		email = frappe.db.get_value("Account Request", account_request, "email")
		free_email_providers = {
			"gmail.com",
			"yahoo.com",
			"hotmail.com",
			"outlook.com",
			"aol.com",
			"icloud.com",
			"mail.com",
			"zoho.com",
			"protonmail.com",
			"gmx.com",
			"yandex.com",
			"live.com",
			"me.com",
			"msn.com",
			"googlemail.com",
			"163.com",
			"sina.com",
			"qq.com",
			"naver.com",
			"hanmail.net",
			"daum.net",
			"nate.com",
			"yahoo.co.jp",
			"yahoo.co.in",
			"yahoo.co.uk",
			"hotmail.co.uk",
			"live.co.uk",
			"outlook.in",
			"rediffmail.com",
		}

		if email and "@" in email:
			domain = email.split("@")[1].lower()
			if domain not in free_email_providers:
				suggested_subdomain = domain.split(".")[0]
				if len(suggested_subdomain) < 5:
					suggested_subdomain += f"-{domain.split('.')[1]}"

				return suggested_subdomain

		return self.get_unique_site_name()

	def get_unique_site_name(self):
		filters = {
			"subdomain": f"{self.name}-{generate_random_name(segment_length=3, num_segments=2)}",
			"domain": self.domain,
			"status": ("!=", "Archived"),
		}
		while frappe.db.exists("Site", filters):
			filters["subdomain"] = f"{self.name}-{generate_random_name(segment_length=3, num_segments=2)}"
		return filters["subdomain"]

	def get_server_from_cluster(self, cluster):
		"""Return the server with the least number of standby sites in the cluster"""
		ReleaseGroupServer = frappe.qb.DocType("Release Group Server")
		Server = frappe.qb.DocType("Server")
		Bench = frappe.qb.DocType("Bench")
		Site = frappe.qb.DocType("Site")
		min_server = (
			frappe.qb.from_(ReleaseGroupServer)
			.select(
				ReleaseGroupServer.server,
				Count(Site.name).as_("site_count"),
			)
			.distinct()
			.where(ReleaseGroupServer.parent == self.release_group)
			.join(Server)
			.on(Server.name == ReleaseGroupServer.server)
			.where(Server.cluster == cluster)
			.join(Bench)
			.on(Bench.server == ReleaseGroupServer.server)
			.left_join(Site)
			.on(Site.server == ReleaseGroupServer.server & Site.status != "Archived" & Site.is_standby == 1)
			.groupby(ReleaseGroupServer.server)
			.orderby(Count(Site.name))
			.limit(1)
			.run(as_dict=True)
		)
		return min_server[0]["server"] if min_server else None


def create_free_app_subscription(app: str, site: str | None = None):
	from press.utils import get_current_team

	free_plan = frappe.get_all(
		"Marketplace App Plan",
		{"enabled": 1, "price_usd": ("<=", 0), "app": app},
		pluck="name",
	)
	if not free_plan:
		return None
	return frappe.get_doc(
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


def get_app_subscriptions_site_config(apps: list[str], site: str | None = None) -> dict:
	subscriptions = []
	site_config: dict[str, Any] = {}

	for app in apps:
		if not (s := create_free_app_subscription(app, site)):
			continue
		subscriptions.append(s)
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
		if has_job_timeout_exceeded():
			return
		product: ProductTrial = frappe.get_doc("Product Trial", product)
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
	inline_images = []
	if product_trial.email_full_logo:
		args.update({"image_path": get_url(product_trial.email_full_logo, True)})
		try:
			logo_name = product_trial.email_full_logo[1:]
			args.update({"logo_name": logo_name})
			with open(frappe.utils.get_site_path("public", logo_name), "rb") as logo_file:
				inline_images.append(
					{
						"filename": logo_name,
						"filecontent": logo_file.read(),
					}
				)
		except Exception as ex:
			log_error(
				"Error reading logo for inline images in email",
				data=ex,
			)
	if product_trial.email_account:
		sender = frappe.get_value("Email Account", product_trial.email_account, "email_id")

	frappe.sendmail(
		sender=sender,
		recipients=email,
		subject=subject,
		template="product_trial_verify_account",
		args=args,
		now=True,
		inline_images=inline_images,
	)


def sync_product_site_users():
	"""Fetch and sync users from product sites, so that they can be used for login to the site from FC."""

	product_groups = frappe.db.get_all(
		"Product Trial", {"published": 1}, ["release_group"], pluck="release_group"
	)
	product_benches = frappe.get_all(
		"Bench", {"group": ("in", product_groups), "status": "Active"}, pluck="name"
	)
	for bench_name in product_benches:
		frappe.enqueue_doc(
			"Bench",
			bench_name,
			"sync_product_site_users",
			queue="sync",
			job_id=f"sync_product_site_users||{bench_name}",
			deduplicate=True,
			enqueue_after_commit=True,
		)


def send_suspend_mail(site_name: str, product_name: str) -> None:
	"""Send suspension mail to the site owner."""

	site = frappe.db.get_value(
		"Site", site_name, ["team", "trial_end_date", "name", "host_name"], as_dict=True
	)
	product = frappe.db.get_value(
		"Product Trial",
		product_name,
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
	inline_images = []
	# TODO: enable it when we use the full logo
	# if product.email_full_logo:
	# 	args.update({"image_path": get_url(product.email_full_logo, True)})
	if product.logo:
		args.update({"logo": get_url(product.logo, True), "title": product.title})
		try:
			logo_name = product.logo[1:]
			args.update({"logo_name": logo_name})
			with open(frappe.utils.get_site_path("public", logo_name), "rb") as logo_file:
				inline_images.append(
					{
						"filename": logo_name,
						"filecontent": logo_file.read(),
					}
				)
		except Exception as ex:
			log_error(
				"Error reading logo for inline images in email",
				data=ex,
			)
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
		inline_images=inline_images,
	)
