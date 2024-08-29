# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from contextlib import suppress


def whitelist_saas_api(func):
	def whitelist_wrapper(fn):
		return frappe.whitelist(allow_guest=True, methods=["POST"])(fn)

	def auth_wrapper(*args, **kwargs):
		headers = frappe.request.headers
		siteAccessToken = headers.get("x-site-access-token")
		site = None
		siteToken = None
		# check when x-site-access-token is provided
		if siteAccessToken:
			splitted = siteAccessToken.split(":")
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
				siteToken = frappe.db.get_value("Site", site, "saas_communication_secret")
		# check when x-site and x-site-token are provided
		else:
			# set site and site token from headers
			site = headers.get("x-site")
			siteToken = headers.get("x-site-token")

		# check for valid values
		if not site or not siteToken:
			frappe.throw(
				"(x-site and x-site-token) or x-site-access-token headers are mandatory",
				frappe.AuthenticationError,
			)

		# validate site
		siteRecord = frappe.get_value(
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
		if not siteRecord:
			frappe.throw("Invalid x-site provided", frappe.AuthenticationError)
		if siteRecord.saas_communication_secret != siteToken:
			frappe.throw("Invalid x-site-token provided", frappe.AuthenticationError)
		if siteRecord.is_standby is None and siteRecord.standby_for_product is None:
			frappe.throw("Sorry, this is not SaaS site", frappe.AuthenticationError)

		# set site and team name in context
		frappe.local.site_name = siteRecord.name
		frappe.local.team_name = siteRecord.team

		# set team user as current user
		frappe.set_user(frappe.get_value("Team", siteRecord.team, "user"))

		# set utility function to get team and site info
		frappe.local.get_site = lambda: frappe.get_doc("Site", frappe.local.site_name)
		frappe.local.get_team = lambda: frappe.get_doc("Team", frappe.local.team_name)

		# remove cmd from kwargs
		kwargsCopy = kwargs.copy()
		kwargsCopy.pop("cmd", None)
		
		return func(*args, **kwargsCopy)

	return whitelist_wrapper(auth_wrapper)
