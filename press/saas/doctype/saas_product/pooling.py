import frappe
from frappe.model.naming import make_autoname
from press.utils import log_error


class SitePool:
	def __init__(self, product):
		self.product = product
		self.site_count = frappe.db.count(
			"Site", filters={"is_standby": True, "status": "Active", "standby_for_product": self.product}
		)
		self.saas_product = frappe.get_doc("SaaS Product", product)

	def create_or_rename(self, subdomain, team):
		standby_site = self.get_standby_site()
		if standby_site:
			site = frappe.get_doc("Site", standby_site)
			site.subdomain = subdomain
			site.is_standby = False
			site.team = team
			site.save(ignore_permissions=True)
			# site.create_subscription()
			return site
		else:
			return self.create_site(subdomain, team)

	def create_site(self, subdomain, team):
		site = frappe.get_doc(
			{
				"doctype": "Site",
				"subdomain": subdomain,
				"domain": self.saas_product.domain,
				"group": self.saas_product.group,
				"cluster": self.saas_product.cluster,
				"is_standby": True,
				"standby_for_product": self.product,
				"team": team,
				"apps": [{"app": d.app} for d in self.saas_product.apps],
			}
		)
		site.insert()

	def create_standby_sites(self):
		if (
			self.saas_product.enable_pooling
			and self.site_count < self.saas_product.standby_pool_size
		):
			sites_created = 0
			while sites_created < self.saas_product.standby_queue_size:
				self.create_standby()
				frappe.db.commit()
				sites_created += 1

	def create_standby(self):
		administrator = frappe.db.get_value("Team", {"user": "Administrator"}, "name")
		site = frappe.get_doc(
			{
				"doctype": "Site",
				"subdomain": self.get_subdomain(),
				"domain": self.saas_product.domain,
				"group": self.saas_product.release_group,
				"cluster": self.saas_product.cluster,
				"is_standby": True,
				"standby_for_product": self.product,
				"team": administrator,
				"apps": [{"app": d.app} for d in self.saas_product.apps],
			}
		)
		site.insert()

	def get_subdomain(self):
		return make_autoname("standby-.########")

	def get_standby_site(self):
		filters = {
			"is_standby": True,
			"standby_for_product": self.product,
			"status": "Active",
		}
		sites = frappe.db.get_all("Site", filters, pluck="name", order_by="creation asc", limit=1)
		return sites[0] if sites else None


def create():
	'''Create standby sites for all products with pooling enabled. This is called by the scheduler.'''
	products = frappe.get_all("SaaS Product", {"enable_pooling": 1}, pluck="name")
	for product in products:
		try:
			SitePool(product).create_standby_sites()
			frappe.db.commit()
		except Exception:
			log_error("Pool Job Error", product=product)
			frappe.db.rollback()
