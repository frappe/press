# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import cstr
from press.api.site import get_installed_apps


class SiteApp(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		site = cstr(filters.get("parent", "")) if filters else None
		if not site:
			return None

		site_doc = frappe.get_doc("Site", site)
		installed_apps = get_installed_apps(site_doc)

		# Apply is_app_patched flag to installed_apps
		app_names = [a.app for a in site_doc.apps]
		patched_apps = frappe.get_all(
			"App Patch",
			fields=["app"],
			filters={
				"bench": site_doc.bench,
				"app": ["in", app_names],
			},
			pluck="app",
		)
		for app in installed_apps:
			if app.app in patched_apps:
				app.is_app_patched = True

		return installed_apps
