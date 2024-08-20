# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe


def whitelist_saas_api(func):
	def whitelist_wrapper(fn):
		return frappe.whitelist(allow_guest=True)(fn)

	def auth_wrapper():
		# check for x-site and x-site-token headers
		headers = frappe.request.headers
		if not headers.get("x-site") or not headers.get("x-site-token"):
			frappe.throw(
				"x-site and x-site-token headers are mandatory", frappe.AuthenticationError
			)

		# validate site
		site = frappe.get_value(
			"Site",
			headers["x-site"],
			[
				"name",
				"team",
				"is_standby",
				"standby_for_product",
				"saas_communication_secret",
			],
			as_dict=True,
			ignore=True,
		)
		if not site:
			frappe.throw("Invalid site", frappe.AuthenticationError)
		if site.saas_communication_secret != headers["x-site-token"]:
			frappe.throw("Invalid token", frappe.AuthenticationError)
		if site.is_standby is None and site.standby_for_product is None:
			frappe.throw("Sorry, this is not SaaS site", frappe.AuthenticationError)

		# set site and team name in context
		frappe.local.site_name = headers["x-site"]
		frappe.local.team_name = site.team

		# set team user as current user
		frappe.set_user(frappe.get_value("Team", site.team, "user"))

		# set utility function to get team and site info
		frappe.local.get_site = lambda: frappe.get_doc("Site", frappe.local.site_name)
		frappe.local.get_team = lambda: frappe.get_doc("Team", frappe.local.team_name)
		return func()

	return whitelist_wrapper(auth_wrapper)
