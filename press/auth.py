# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import json
import traceback
import os

PRESS_AUTH_KEY = "press-auth-logs"
PRESS_AUTH_MAX_ENTRIES = 1000000


ALLOWED_PATHS = [
	"/api/method/create-site-migration",
	"/api/method/create-version-upgrade",
	"/api/method/migrate-to-private-bench",
	"/api/method/find-my-sites",
	"/api/method/frappe.core.doctype.communication.email.mark_email_as_seen",
	"/api/method/frappe.realtime.get_user_info",
	"/api/method/frappe.www.login.login_via_frappe",
	"/api/method/frappe.website.doctype.web_page_view.web_page_view.make_view_log",
	"/api/method/get-user-sites-list-for-new-ticket",
	"/api/method/login",
	"/api/method/logout",
	"/api/method/press.press.doctype.razorpay_webhook_log.razorpay_webhook_log.razorpay_webhook_handler",
	"/api/method/press.press.doctype.stripe_webhook_log.stripe_webhook_log.stripe_webhook_handler",
	"/api/method/upload_file",
	"/api/method/frappe.search.web_search",
	"/api/method/frappe.email.queue.unsubscribe",
	"/api/method/frappe.client.get",
	"/api/method/frappe.client.get_count",
]

ALLOWED_WILDCARD_PATHS = [
	"/api/method/frappedesk.",
	"/api/method/press.api.",
]

DENIED_WILDCARD_PATHS = [
	"/api/",
]


def hook():
	if frappe.form_dict.cmd:
		path = f"/api/method/{frappe.form_dict.cmd}"
	else:
		path = frappe.request.path

	user_type = frappe.get_cached_value("User", frappe.session.user, "user_type")

	# Allow unchecked access to System Users
	if user_type == "System User":
		return

	for denied in DENIED_WILDCARD_PATHS:
		if path.startswith(denied):
			for allowed in ALLOWED_WILDCARD_PATHS:
				if path.startswith(allowed):
					return
			if path in ALLOWED_PATHS:
				return

			log(path, user_type)
			frappe.throw("Access not allowed for this URL", frappe.AuthenticationError)

	return


def log(path, user_type):
	data = {
		"ip": frappe.local.request_ip,
		"timestamp": frappe.utils.now(),
		"user_type": user_type,
		"path": path,
		"user": frappe.session.user,
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
