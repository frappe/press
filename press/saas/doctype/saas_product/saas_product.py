# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.naming import make_autoname
from frappe.model.document import Document
from press.utils import log_error


class SaaSProduct(Document):
	dashboard_fields = ["title", "logo", "description", "domain", "trial_days"]

	def get_doc(self, doc):
		if not self.published:
			frappe.throw("Not permitted")
		doc.description = frappe.utils.md_to_html(self.description)
		doc.proxy_servers = self.get_proxy_servers_for_available_clusters()
		return doc

	def setup_trial_site(self, subdomain, team, cluster=None):
		standby_site = self.get_standby_site(cluster)
		if not standby_site:
			frappe.throw("There was an error setting up the trial site")

		site = frappe.get_doc("Site", standby_site)
		site.subdomain = subdomain
		site.is_standby = False
		site.team = team
		site.save(ignore_permissions=True)
		return site

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
		public_clusters = frappe.db.get_all(
			"Cluster", {"name": ("in", clusters), "public": 1}, order_by="name asc", pluck="name"
		)
		return public_clusters

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

	def create_standby_sites_in_each_cluster(self):
		if not self.enable_pooling:
			return

		clusters = self.get_available_clusters()
		for cluster in clusters:
			self.create_standby_sites(cluster)

	def create_standby_sites(self, cluster):
		if not self.enable_pooling:
			return
		standby_site_count = frappe.db.count(
			"Site",
			{
				"cluster": cluster,
				"is_standby": 1,
				"standby_for_product": self.name,
				"status": "Active",
			},
		)
		sites_to_create = self.standby_pool_size - standby_site_count
		if sites_to_create <= 0:
			return
		if sites_to_create > self.standby_queue_size:
			sites_to_create = self.standby_queue_size

		for i in range(sites_to_create):
			self.create_standby_site(cluster)
			frappe.db.commit()

	def create_standby_site(self, cluster):
		administrator = frappe.db.get_value("Team", {"user": "Administrator"}, "name")
		site = frappe.get_doc(
			doctype="Site",
			subdomain=make_autoname("standby-.########"),
			domain=self.domain,
			group=self.release_group,
			cluster=cluster,
			is_standby=True,
			standby_for_product=self.name,
			team=administrator,
			apps=[{"app": d.app} for d in self.apps],
		)
		site.insert()


def replenish_standby_sites():
	"""Create standby sites for all products with pooling enabled. This is called by the scheduler."""
	products = frappe.get_all("SaaS Product", {"enable_pooling": 1}, pluck="name")
	for product in products:
		product = frappe.get_doc("SaaS Product", product)
		try:
			product.create_standby_sites_in_each_cluster()
			frappe.db.commit()
		except Exception:
			log_error("Replenish Standby Sites Error", product=product.name)
			frappe.db.rollback()
