# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json


def log_error(title, **kwargs):
	traceback = frappe.get_traceback()
	serialized = json.dumps(kwargs, indent=4, sort_keys=True)
	message = f"Data:\n{serialized}\nException:\n{traceback}"
	frappe.log_error(title=title, message=message)


def get_formated_date(timestamp):
	from datetime import datetime
	date_format = "%Y-%m-%d"
	return datetime.fromtimestamp(timestamp).strftime(date_format)


def get_current_team():
	if not hasattr(frappe.local, "request"):
		# if this is not a request, send the current user as default team
		return frappe.session.user

	# get team passed via request header
	team = frappe.get_request_header("X-Press-Team")
	if not team:
		frappe.throw("Invalid Team", frappe.PermissionError)
	return team
