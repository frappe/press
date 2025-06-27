import frappe
from frappe.model.naming import make_autoname

from press.press.doctype.site.saas_site import (
	create_app_subscriptions,
	get_pool_apps,
	get_saas_apps,
	get_saas_bench,
	get_saas_domain,
	set_site_in_subscription_docs,
)
from press.utils import log_error


class SaasSitePool:
	def __init__(self, app):
		self.app = app
		self.site_count = frappe.db.count(
			"Site",
			filters={
				"is_standby": True,
				"status": ["in", ["Active", "Pending", "Installing", "Updating", "Recovering"]],
				"standby_for": self.app,
				"hybrid_saas_pool": "",
			},
		)
		self.saas_settings = frappe.get_doc("Saas Settings", app)

	def create(self):
		if self.saas_settings.enable_pooling:
			if self.site_count < self.saas_settings.standby_pool_size:
				sites_created = 0
				while sites_created < self.saas_settings.standby_queue_size:
					self.create_one()
					frappe.db.commit()
					sites_created += 1

			if frappe.db.get_value("Saas Settings", self.app, "enable_hybrid_pools"):
				self.create_hybrid_pool_sites()

	def create_one(self, pool_name: str = ""):
		bench, apps, subdomain, domain = None, None, None, None
		try:
			domain = get_saas_domain(self.app)
			bench = get_saas_bench(self.app)
			subdomain = self.get_subdomain()
			apps = get_saas_apps(self.app)
			if pool_name:
				apps.extend(get_pool_apps(pool_name))
			site = frappe.get_doc(
				{
					"doctype": "Site",
					"subdomain": subdomain,
					"domain": domain,
					"is_standby": True,
					"standby_for": self.app,
					"hybrid_saas_pool": pool_name,
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
			hybrid_standby_count = frappe.db.count(
				"Site",
				{
					"is_standby": 1,
					"standby_for": self.app,
					"hybrid_saas_pool": pool_name,
					"status": ("in", ["Active", "Pending", "Installing", "Updating", "Recovering"]),
				},
			)

			if hybrid_standby_count > self.saas_settings.standby_pool_size:
				continue

			sites_created = 0
			while sites_created < self.saas_settings.standby_queue_size:
				self.create_one(pool_name)
				frappe.db.commit()
				sites_created += 1

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
