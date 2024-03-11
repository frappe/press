import frappe
from frappe.model.naming import make_autoname
from press.utils import log_error
from press.press.doctype.site.saas_site import (
	get_saas_bench,
	get_saas_apps,
	get_saas_domain,
	get_pool_apps,
	create_app_subscriptions,
	set_site_in_subscription_docs,
)


class SaasSitePool:
	def __init__(self, app):
		self.app = app
		self.site_count = frappe.db.count(
			"Site", filters={"is_standby": True, "status": "Active", "standby_for": self.app}
		)
		self.saas_settings = frappe.get_doc("Saas Settings", app)

	def create(self):
		if (
			self.saas_settings.enable_pooling
			and self.site_count < self.saas_settings.standby_pool_size
		):
			sites_created = 0
			while sites_created < self.saas_settings.standby_queue_size:
				self.create_one()
				frappe.db.commit()
				sites_created += 1

	def create_one(self):
		bench, apps, subdomain, domain = None, None, None, None
		try:
			if frappe.db.get_value("Saas Settings", self.app, "enable_hybrid_pools"):
				self.create_hybrid_pool_sites()
			domain = get_saas_domain(self.app)
			bench = get_saas_bench(self.app)
			subdomain = self.get_subdomain()
			apps = get_saas_apps(self.app)
			site = frappe.get_doc(
				{
					"doctype": "Site",
					"subdomain": subdomain,
					"domain": domain,
					"is_standby": True,
					"standby_for": self.app,
					"team": frappe.get_value("Team", {"user": "Administrator"}, "name"),
					"bench": bench,
					"apps": [{"app": app} for app in apps],
				}
			)
			subscription_docs = create_app_subscriptions(site, self.app)
			site.insert()
			set_site_in_subscription_docs(subscription_docs, site.name)
		except Exception:
			log_error(
				"Pool Site Creation Error",
				domain=domain,
				subdomain=subdomain,
				bench=bench,
				apps=apps,
			)
			raise

	def create_hybrid_pool_sites(self):
		# create a Site according to Site Rules child table in each Hybrid Saas Pool
		for pool_name in frappe.get_all("Hybrid Saas Pool", {"app": self.app}, pluck="name"):
			# only has app rules for now, will add site config and other rules later
			pool_apps = get_pool_apps(pool_name)
			domain = get_saas_domain(self.app)
			bench = get_saas_bench(self.app)
			subdomain = self.get_subdomain()
			apps = get_saas_apps(self.app)
			apps.extend(pool_apps)
			site = frappe.get_doc(
				{
					"doctype": "Site",
					"subdomain": subdomain,
					"domain": domain,
					"is_standby": True,
					"hybrid_saas_pool": pool_name,
					"standby_for": self.app,
					"team": "Administrator",
					"bench": bench,
					"apps": [{"app": app} for app in apps],
				}
			)
			subscription_docs = create_app_subscriptions(site, self.app)
			site.insert()
			set_site_in_subscription_docs(subscription_docs, site.name)

	def get_subdomain(self):
		return make_autoname("standby-.########")

	def get(self, hybrid_saas_pool):
		filters = {
			"is_standby": True,
			"standby_for": self.app,
			"status": "Active",
		}

		if hybrid_saas_pool:
			filters.update({"hybrid_saas_pool": hybrid_saas_pool})
		else:
			filters.update({"hybrid_saas_pool": ("is", "not set")})

		sites = frappe.get_all("Site", filters, pluck="name", order_by="creation", limit=1)

		return sites[0] if sites else sites


def create():
	saas_apps = frappe.get_all("Saas Settings", {"enable_pooling": 1}, pluck="name")
	for app in saas_apps:
		try:
			SaasSitePool(app).create()
			frappe.db.commit()
		except Exception:
			log_error("Pool Error", app=app)
			frappe.db.rollback()


def get(app, hybrid_saas_pool=""):
	return SaasSitePool(app).get(hybrid_saas_pool)
