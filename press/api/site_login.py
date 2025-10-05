# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.rate_limiter import rate_limit


@frappe.whitelist(allow_guest=True, methods=["POST"])
def sync_product_site_user(**data):
	"""
	Sync user info from product site

	Warning: Do not change the function name since it is used in production sites to sync user info
	"""
	import json

	headers = frappe.request.headers
	site = headers.get("x-site")
	site_token = headers.get("x-site-token")

	if not frappe.db.exists("Site", site):
		frappe.throw("Invalid site")

	if not site_token:
		frappe.throw("Invalid communication secret")

	site = frappe.db.get_value("Site", site, ["saas_communication_secret", "name"], as_dict=True)

	if site.saas_communication_secret != site_token:
		frappe.throw("Invalid token")

	user_info = data.get("user_info")

	if not user_info:
		frappe.throw("No user info provided")

	if type(user_info) is str:
		user_info = json.loads(user_info)

	user_mail = user_info.get("email")
	enabled = user_info.get("enabled")
	if frappe.db.exists("Site User", {"site": site.name, "user": user_mail}):
		user = frappe.db.get_value(
			"Site User", {"site": site.name, "user": user_mail}, ["name", "enabled"], as_dict=True
		)
		if user.enabled != enabled:
			frappe.db.set_value("Site User", user.name, "enabled", enabled)
	else:
		frappe.get_doc(
			{
				"doctype": "Site User",
				"site": site.name,
				"user": user_mail,
				"enabled": enabled,
			}
		).insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 5)
def send_otp(email: str):
	"""
	Send OTP to the user trying to login to the product site from /site-login page
	"""

	last_otp = frappe.db.get_value("Site User Session", {"user": email}, "otp_generated_at")
	if last_otp and (frappe.utils.now_datetime() - last_otp).seconds < 30:
		return frappe.throw("Please wait for 30 seconds before sending the OTP again")

	session = frappe.get_doc({"doctype": "Site User Session", "user": email}).insert(ignore_permissions=True)
	return session.send_otp()


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def verify_otp(email: str, otp: str):
	"""
	Verify OTP
	"""
	from frappe.auth import get_login_attempt_tracker

	session = frappe.db.get_value(
		"Site User Session", {"user": email}, ["name", "session_id", "otp", "otp_generated_at"], as_dict=True
	)
	if not session:
		return frappe.throw("Invalid session")

	if not session.otp:
		return frappe.throw("OTP is not set")

	if (frappe.utils.now_datetime() - session.otp_generated_at).seconds > 300:
		return frappe.throw("OTP is expired")

	ip_tracker = get_login_attempt_tracker(frappe.local.request_ip)

	if session.otp != otp:
		ip_tracker and ip_tracker.add_failure_attempt()
		return frappe.throw("Invalid OTP")

	frappe.db.set_value("Site User Session", session.name, {"otp": None, "verified": 1})
	ip_tracker and ip_tracker.add_success_attempt()

	five_days_in_seconds = 5 * 24 * 60 * 60
	return frappe.local.cookie_manager.set_cookie(
		"site_user_sid", session.session_id, max_age=five_days_in_seconds, httponly=True
	)
