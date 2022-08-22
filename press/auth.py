# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import json
import traceback
import os

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
		"referer": frappe.request.headers.get("Referer", ""),
	}

	if frappe.cache().llen(PRESS_AUTH_KEY) > PRESS_AUTH_MAX_ENTRIES:
		frappe.cache().ltrim(PRESS_AUTH_KEY, 1, -1)
	serialized = json.dumps(data, sort_keys=True, default=str)
	frappe.cache().rpush(PRESS_AUTH_KEY, serialized)


def flush():
	log_file = os.path.join(frappe.utils.get_bench_path(), "logs", "press.auth.json.log")
	try:
		# Fetch all entries without removing from cache
		logs = frappe.cache().lrange(PRESS_AUTH_KEY, 0, -1)
		if logs:
			logs = list(map(frappe.safe_decode, logs))
			with open(log_file, "a", os.O_NONBLOCK) as f:
				f.write("\n".join(logs))
				f.write("\n")
			# Remove fetched entries from cache
			frappe.cache().ltrim(PRESS_AUTH_KEY, len(logs) - 1, -1)
	except Exception:
		traceback.print_exc()
