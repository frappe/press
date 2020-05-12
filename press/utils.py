# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import requests


def log_error(title, **kwargs):
	traceback = frappe.get_traceback()
	serialized = json.dumps(kwargs, indent=4, sort_keys=True, default=str, skipkeys=True)
	message = f"Data:\n{serialized}\nException:\n{traceback}"
	frappe.log_error(title=title, message=message)


def get_current_team():
	if not hasattr(frappe.local, "request"):
		# if this is not a request, send the current user as default team
		return frappe.session.user

	# get team passed via request header
	team = frappe.get_request_header("X-Press-Team")

	if not frappe.db.exists("Team", team):
		frappe.throw("Invalid Team", frappe.PermissionError)

	valid_team = frappe.db.exists(
		"Team Member", {"parenttype": "Team", "parent": team, "user": frappe.session.user}
	)
	if not valid_team:
		frappe.throw(
			"User {0} does not belong to Team {1}".format(frappe.session.user, team),
			frappe.PermissionError,
		)

	return team


def get_country_info():
	ip = frappe.local.request_ip
	ip_api_key = frappe.conf.get("ip-api-key")

	def _get_country_info():
		fields = ["countryCode", "country", "regionName", "city"]
		res = requests.get(
			"https://pro.ip-api.com/json/{ip}?key={key}&fields={fields}".format(
				ip=ip, key=ip_api_key, fields=",".join(fields)
			)
		)
		try:
			data = res.json()
			if data.get("status") != "fail":
				return data
		except Exception:
			pass

		return {}

	return frappe.cache().hget("ip_country_map", ip, generator=_get_country_info)
