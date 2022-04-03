import frappe
from press.press.doctype.site.site import Site
from press.press.doctype.account_request.account_request import AccountRequest


class SaasSite(Site):
	def __init__(self, site=None, app=None, account_request: AccountRequest = None):
		self.app = app
		if site:
			super().__init__("Site", site)
		elif account_request:
			super().__init__(
				{
					"doctype": "Site",
					"subdomain": account_request.subdomain,
					"domain": get_saas_domain(self.app),
					"bench": get_saas_bench(self.app),
					"apps": [{"app": app} for app in get_saas_apps(self.app)],
					"team": "Administrator",
					"account_request": account_request.name,
					"subscription_plan": get_saas_plan(self.app),
					"trial_end_date": frappe.utils.add_days(None, 7),
				}
			)

	def rename_pooled_site(self, account_request):
		self.subdomain = account_request.subdomain
		self.is_standby = False
		self.account_request = account_request.name
		self.trial_end_date = frappe.utils.add_days(None, 7)
		plan = get_saas_plan(self.app)
		self._update_configuration(self.get_plan_config(plan), save=False)
		self.save(ignore_permissions=True)
		self.create_subscription(plan)

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
	return frappe.db.get_single_value("Saas Settings", f"{app}_plan")


def get_saas_domain(app):
	return frappe.db.get_single_value("Saas Settings", f"{app}_domain")


def get_saas_cluster(app):
	return frappe.db.get_single_value("Saas Settings", f"{app}_cluster")


def get_saas_apps(app):
	return [
		app["app"] for app in frappe.get_doc("Press Settings").as_dict()[f"{app}_apps"]
	]


def get_saas_group(app):
	return frappe.db.get_single_value("Saas Settings", f"{app}_group")
