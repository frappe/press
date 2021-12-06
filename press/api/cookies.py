import json
import frappe
import datetime

from urllib.parse import unquote
from frappe.auth import CookieManager
from frappe.oauth import get_cookie_dict_from_headers


@frappe.whitelist(allow_guest=True)
def update_preferences(preferences):
	preferences_dict = json.loads(preferences)

	if not frappe.local.cookie_manager:
		frappe.local.cookie_manager = CookieManager()

	cookie_manager = frappe.local.cookie_manager
	cookie_perms = get_cookie_dict_from_headers(frappe.local.request).get("cookie_perms")

	if cookie_perms:
		cookie_perms = json.loads(unquote(cookie_perms.value))

		# If was disabled before, now enabled or vice-versa
		if cookie_perms.get("analytics") != preferences_dict.get("analytics"):
			log_cookie_consent(preferences_dict)
	else:
		# Enabled for the first time
		if preferences_dict.get("analytics"):
			log_cookie_consent(preferences_dict)

	# Update the cookie
	expires = datetime.datetime.now() + datetime.timedelta(days=180)
	cookie_manager.set_cookie("cookie_perms", preferences, expires=expires)


def log_cookie_consent(preferences):
	frappe.get_doc(
		{
			"doctype": "Cookie Preference Log",
			"ip_address": frappe.local.request_ip,
			"agreed_to_analytics_cookies": preferences.get("analytics"),
			"agreed_to_functionality_cookies": preferences.get("functionality"),
			"agreed_to_performance_cookies": preferences.get("performance"),
		}
	).insert(ignore_permissions=True)
