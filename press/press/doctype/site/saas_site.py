import frappe
import json
from press.press.doctype.site.site import Site
from press.press.doctype.account_request.account_request import AccountRequest


class SaasSite(Site):
	def __init__(
		self,
		site=None,
		app=None,
		account_request: AccountRequest = None,
		hybrid_saas_pool=None,
		subdomain=None,
	):
		self.app = app
		if site:
			super().__init__("Site", site)
		else:
			ar_name = account_request.name if account_request else ""
			subdomain = account_request.subdomain if account_request else subdomain
			apps = get_saas_apps(self.app)
			if hybrid_saas_pool:
				# set pool apps
				pool_apps = get_pool_apps(hybrid_saas_pool)
				apps.extend(pool_apps)

			super().__init__(
				{
					"doctype": "Site",
					"subdomain": subdomain,
					"domain": get_saas_domain(self.app),
					"bench": get_saas_bench(self.app),
					"apps": [{"app": app} for app in apps],
					"team": "Administrator",
					"standby_for": self.app,
					"hybrid_saas_pool": hybrid_saas_pool,
					"account_request": ar_name,
					"subscription_plan": get_saas_site_plan(self.app),
					"trial_end_date": frappe.utils.add_days(None, 14),
				}
			)

			self.subscription_docs = create_app_subscriptions(site=self, app=self.app)

	def rename_pooled_site(self, account_request=None, subdomain=None):
		self.subdomain = account_request.subdomain if account_request else subdomain
		self.is_standby = False
		self.account_request = account_request.name if account_request else ""
		self.trial_end_date = frappe.utils.add_days(None, 14)
		plan = get_saas_site_plan(self.app)
		self._update_configuration(self.get_plan_config(plan), save=False)
		self.save(ignore_permissions=True)
		self.create_subscription(plan)

		return self

	def can_change_plan(self):
		return True

	def can_create_site(self):
		return True


def get_saas_bench(app):
	domain = get_saas_domain(app)
	cluster = get_saas_cluster(app)

	proxy_servers = frappe.get_all(
		"Proxy Server",
		[
			["status", "=", "Active"],
			["cluster", "=", cluster],
			["Proxy Server Domain", "domain", "=", domain],
		],
		pluck="name",
	)
	release_group = get_saas_group(app)
	query = """
		SELECT
			bench.name
		FROM
			tabBench bench
		LEFT JOIN
			tabServer server
		ON
			bench.server = server.name
		WHERE
			server.proxy_server in %s AND bench.status = "Active" AND bench.group = %s
		ORDER BY
			server.use_for_new_sites DESC, bench.creation DESC
		LIMIT 1
	"""
	return frappe.db.sql(query, [proxy_servers, release_group], as_dict=True)[0].name


def get_saas_plan(app):
	return frappe.db.get_value("Saas Settings", app, "plan")


def get_saas_site_plan(app):
	return frappe.db.get_value("Saas Settings", app, "site_plan")


def get_saas_domain(app):
	return frappe.db.get_value("Saas Settings", app, "domain")


def get_saas_cluster(app):
	return frappe.db.get_value("Saas Settings", app, "cluster")


def get_saas_apps(app):
	return [_app["app"] for _app in frappe.get_doc("Saas Settings", app).as_dict()["apps"]]


def get_saas_group(app):
	return frappe.db.get_value("Saas Settings", app, "group")


def get_pool_apps(pool_name):
	pool_apps = []
	for rule in frappe.get_doc("Hybrid Saas Pool", pool_name).as_dict()["site_rules"]:
		if rule.rule_type == "App":
			pool_apps.append(rule.app)

	return pool_apps


def get_default_team_for_app(app):
	return frappe.db.get_value("Saas Settings", app, "default_team")


# Saas Update site config utils


def create_app_subscriptions(site, app):
	marketplace_apps = (
		get_saas_apps(app)
		if frappe.db.get_value("Saas Settings", app, "multi_subscription")
		else app
	)

	# create subscriptions
	subscription_docs, custom_saas_config = get_app_subscriptions(marketplace_apps)

	# set site config
	site_config = {f"sk_{s.app}": s.secret_key for s in subscription_docs}
	site_config.update(custom_saas_config)
	site._update_configuration(site_config, save=False)

	return subscription_docs


def get_app_subscriptions(apps=None):
	subscriptions = []
	custom_saas_config = {}

	for app in apps:
		free_plan = frappe.get_all(
			"Marketplace App Plan", {"enabled": 1, "is_free": 1, "app": app}, pluck="name"
		)
		if free_plan:
			new_subscription = frappe.get_doc(
				{
					"doctype": "Marketplace App Subscription",
					"marketplace_app_plan": get_saas_plan(app)
					if frappe.db.exists("Saas Settings", app)
					else free_plan[0],
					"app": app,
					"while_site_creation": True,
					"status": "Disabled",
				}
			).insert(ignore_permissions=True)

			subscriptions.append(new_subscription)
			config = frappe.db.get_value("Marketplace App", app, "site_config")
			config = json.loads(config) if config else {}
			custom_saas_config.update(config)

	return subscriptions, custom_saas_config


def set_site_in_subscription_docs(subscription_docs, site):
	for doc in subscription_docs:
		doc.site = site
		doc.save(ignore_permissions=True)
