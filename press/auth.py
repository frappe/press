# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import json

PRESS_AUTH_KEY = "press-auth-logs"
PRESS_AUTH_MAX_ENTRIES = 1000000


def hook():
	if frappe.form_dict.cmd:
		path = f"/api/request/{frappe.form_dict.cmd}"
	else:
		path = frappe.request.path

	data = {
		"timestamp": frappe.utils.now(),
		"user_type": frappe.session.data.user_type,
		"path": path,
		"user": frappe.session.data.user,
	}

	if frappe.cache().llen(PRESS_AUTH_KEY) > PRESS_AUTH_MAX_ENTRIES:
		frappe.cache().ltrim(PRESS_AUTH_KEY, 1, -1)
	serialized = json.dumps(data, sort_keys=True, default=str)
	frappe.cache().rpush(PRESS_AUTH_KEY, serialized)
