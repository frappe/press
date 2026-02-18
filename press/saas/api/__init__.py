# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from contextlib import suppress

import frappe


def whitelist_saas_api(func):  # noqa: C901
	def whitelist_wrapper(fn):
		return frappe.whitelist(allow_guest=True, methods=["POST"])(fn)

	def auth_wrapper(*args, **kwargs):
		headers = frappe.request.headers
		site_access_token = headers.get("x-site-access-token")
		site = None
		site_token = None
		# check when x-site-access-token is provided
		if site_access_token:
			splitted = site_access_token.split(":")
			if len(splitted) != 2:
				frappe.throw("Invalid x-site-access-token provided", frappe.AuthenticationError)
			accessTokenDocName = splitted[0]
			token = splitted[1]
			with suppress(frappe.DoesNotExistError):
				record = frappe.get_doc("Site Access Token", accessTokenDocName)
				if record.token != token:
					frappe.throw("Invalid x-site-access-token provided", frappe.AuthenticationError)
				# set site and site token from access token record
				site = record.site
				site_token = frappe.db.get_value("Site", site, "saas_communication_secret")
		# check when x-site and x-site-token are provided
		else:
			# set site and site token from headers
			site = headers.get("x-site")
			site_token = headers.get("x-site-token")

		# check for valid values
		if not site or not site_token:
			frappe.throw(
				"(x-site and x-site-token) or x-site-access-token headers are mandatory",
				frappe.AuthenticationError,
			)

		# validate site
		site_record = frappe.get_value(
			"Site",
			site,
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

		if not site_record:
			frappe.throw("Invalid x-site provided", frappe.AuthenticationError)

		if site_record.saas_communication_secret != site_token:
			frappe.throw("Invalid x-site-token provided", frappe.AuthenticationError)

		if site_record.is_standby is None and site_record.standby_for_product is None:
			frappe.throw("Sorry, this is not a SaaS site", frappe.AuthenticationError)

		# set site and team name in context
		frappe.local.site_name = site_record.name
		frappe.local.team_name = site_record.team

		# set team user as current user
		frappe.set_user(frappe.get_value("Team", site_record.team, "user"))

		# set utility function to get team and site info
		frappe.local.get_site = lambda: frappe.get_doc("Site", frappe.local.site_name)
		frappe.local.get_team = lambda: frappe.get_doc("Team", frappe.local.team_name)

		# remove cmd from kwargs
		kwargsCopy = kwargs.copy()
		kwargsCopy.pop("cmd", None)

		return func(*args, **kwargsCopy)

	return whitelist_wrapper(auth_wrapper)
