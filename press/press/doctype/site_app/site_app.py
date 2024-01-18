# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.api.site import get_installed_apps
from frappe.utils import cstr


class SiteApp(Document):
	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		if filters and filters.get("parent"):
			site_name = cstr(filters.get("parent"))
			site = frappe.get_doc("Site", site_name)
			return get_installed_apps(site)
