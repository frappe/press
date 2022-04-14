import frappe
from frappe.model.naming import make_autoname
from press.utils import log_error
from press.press.doctype.site.saas_site import (
	get_saas_bench,
	get_saas_apps,
	get_saas_domain,
)


class SaasSitePool:
	def __init__(self, app):
		self.app = app
		self.site_count = frappe.db.count(
			"Site", filters={"is_standby": True, "status": "Active", "standby_for": self.app}
		)
		self.pool_size = frappe.db.get_value(
			"Saas Settings",
			app,
			"standby_pool_size",
		)
		self.queue_size = frappe.db.get_value(
			"Saas Settings",
			app,
			"standby_queue_size",
		)

	def create(self):
		pooling_enabled = frappe.db.get_value("Saas Settings", self.app, "enable_pooling")
		if pooling_enabled and self.site_count < self.pool_size:
			sites_created = 0
			while sites_created < self.queue_size:
				self.create_one()
				frappe.db.commit()
				sites_created += 1

	def create_one(self):
		try:
			domain = get_saas_domain(self.app)
			bench = get_saas_bench(self.app)
			subdomain = self.get_subdomain()
			apps = get_saas_apps(self.app)
			frappe.get_doc(
				{
					"doctype": "Site",
					"subdomain": subdomain,
					"domain": domain,
					"is_standby": True,
					"standby_for": self.app,
					"team": "Administrator",
					"bench": bench,
					"apps": [{"app": app} for app in apps],
				}
			).insert()
		except Exception:
			log_error(
				"Pool Site Creation Error",
				domain=domain,
				subdomain=subdomain,
				bench=bench,
				apps=apps,
			)
			raise

	def get_subdomain(self):
		return make_autoname("standby-.########")

	def get(self):
		return frappe.db.get_value(
			"Site",
			{"is_standby": True, "standby_for": self.app, "status": "Active"},
			"name",
			order_by="creation",
		)


def create():
	saas_apps = frappe.get_all("Saas App", pluck="app")
	for app in saas_apps:
		if app == "erpnext":
			SaasSitePool(app).create()


def get(app):
	return SaasSitePool(app).get()
