# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

from datetime import datetime, timedelta
import frappe
from press.utils import get_current_team, log_error
import requests
import jwt


@frappe.whitelist(allow_guest=True)
def hook(*args, **kwargs):
	try:
		headers = frappe.request.headers
		doc = frappe.get_doc(
			{
				"doctype": "GitHub Webhook Log",
				"name": headers.get("X-Github-Delivery"),
				"event": headers.get("X-Github-Event"),
				"signature": headers.get("X-Hub-Signature").split("=")[1],
				"payload": frappe.request.get_data().decode(),
			}
		)
		doc.insert(ignore_permissions=True)
	except Exception:
		log_error("GitHub Webhook Error", args=args, kwargs=kwargs)


