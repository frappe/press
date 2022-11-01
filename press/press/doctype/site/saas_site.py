import frappe
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
