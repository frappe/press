# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.naming import make_autoname
from press.utils import log_error
from press.press.doctype.site.erpnext_site import (
	get_erpnext_bench,
	get_erpnext_apps,
	get_erpnext_domain,
)


class SitePool:
	def __init__(self):
		self.site_count = frappe.db.count(
			"Site", filters={"is_standby": True, "status": "Active"}
		)
		self.pool_size = frappe.db.get_single_value("Press Settings", "standby_pool_size")
		self.queue_size = frappe.db.get_single_value("Press Settings", "standby_queue_size")

	def create(self):
		pooling_enabled = frappe.db.get_single_value("Press Settings", "enable_site_pooling")
		if pooling_enabled and self.site_count < self.pool_size:
			sites_created = 0
			while sites_created < self.queue_size:
				self.create_one()
				frappe.db.commit()
				sites_created += 1

	def create_one(self):
		try:
			domain = get_erpnext_domain()
			bench = get_erpnext_bench()
			subdomain = self.get_subdomain()
			apps = get_erpnext_apps()
			frappe.get_doc(
				{
					"doctype": "Site",
					"subdomain": subdomain,
					"domain": domain,
					"is_standby": True,
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
			{"is_standby": True, "status": "Active", "standby_for": ("=", "")},
			"name",
			order_by="creation",
		)


def create():
	SitePool().create()


def get():
	return SitePool().get()
