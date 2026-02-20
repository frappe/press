# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address

from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.site.site import Site


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
@rate_limit(limit=10, seconds=60)
def get_product_sites_of_user(user: str):
	"""
	Get all product sites of a user
	"""
	if not frappe.db.exists("Site User", {"user": user}):
		return []

	session_id = frappe.local.request.cookies.get("site_user_sid")
	if (
		not session_id
		or not isinstance(session_id, str)
		or not frappe.db.exists("Site User Session", {"user": user, "session_id": session_id})
	) and (frappe.session.user == "Guest"):
		return frappe.throw("Invalid session")

	sites = frappe.db.get_all(
		"Site User", filters={"user": user, "enabled": 1}, fields=["site"], pluck="site"
	)
	return frappe.db.get_all(
		"Site",
		filters={"name": ["in", sites], "status": "Active"},
		fields=[
			"name",
			"trial_end_date",
			"plan.plan_title as plan_title",
			"plan.price_usd as price_usd",
			"plan.price_inr as price_inr",
			"host_name",
		],
	)


def verify_user_in_site(site_doc: "Site", user: str) -> bool:
	try:
		query = f"""
			SELECT name, enabled
			FROM `tabUser`
			WHERE name = '{user}'
		"""
		response = site_doc.run_sql_query_in_database(query, False)
		if (
			response.get("success", False)
			and response.get("data")
			and response["data"][0].get("row_count", 0) == 1
		):
			_, is_user_enabled = response["data"][0]["output"]["data"][0]
			return bool(is_user_enabled)
	except frappe.DoesNotExistError:
		pass
	except Exception as e:
		log_error("Error verifying user in site", data=e)
	return False


def _get_user_product_sites_count(email: str):
	try:
		SiteUser = frappe.qb.DocType("Site User")
		Site = frappe.qb.DocType("Site")
		query = (
			frappe.qb.from_(Site)
			.select(Count(Site.name).as_("site_count"))
			.join(SiteUser)
			.on(SiteUser.site == Site.name)
			.where(SiteUser.user == email)
			.where(SiteUser.enabled == 1)
			.where(Site.status == "Active")
		)
		output = query.run(as_dict=True)
		return output[0].get("site_count", 0) if output else 0
	except Exception as e:
		log_error("Error fetching site count", data=e)
		return 0


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 5)
def send_otp(email: str):
	"""
	Send OTP to the user trying to login to the product site from /site-login page
	"""
	validate_email_address(email, throw=True)
	site_count = _get_user_product_sites_count(email)
	if site_count <= 0:
		frappe.throw("Invalid user")
	last_otp = frappe.db.get_value("Site User Session", {"user": email}, "otp_generated_at")
	if last_otp and (frappe.utils.now_datetime() - last_otp).seconds < 30:
		frappe.throw("Please wait for 30 seconds before sending the OTP again")
	try:
		session = frappe.get_doc({"doctype": "Site User Session", "user": email}).insert(
			ignore_permissions=True
		)
		return session.send_otp()
	except Exception as e:
		log_error("Error sending OTP", data=e)
		frappe.throw("Sending OTP failed")


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
		frappe.throw("Invalid session")

	if not session.otp:
		frappe.throw("OTP is not set")

	if (frappe.utils.now_datetime() - session.otp_generated_at).seconds > 300:
		frappe.throw("OTP is expired")

	ip_tracker = get_login_attempt_tracker(frappe.local.request_ip)

	if session.otp != otp:
		ip_tracker and ip_tracker.add_failure_attempt()
		frappe.throw("Invalid OTP")

	frappe.db.set_value("Site User Session", session.name, {"otp": None, "verified": 1})
	ip_tracker and ip_tracker.add_success_attempt()

	five_days_in_seconds = 5 * 24 * 60 * 60
	return frappe.local.cookie_manager.set_cookie(
		"site_user_sid", session.session_id, max_age=five_days_in_seconds, httponly=True
	)


def verify_session_user(email: str) -> str | None:
	session_id = frappe.local.request.cookies.get("site_user_sid")
	if not session_id or not isinstance(session_id, str):
		return None
	user = frappe.db.get_value("Site User Session", {"session_id": session_id, "verified": 1}, "user")
	return user if user and user == email else None


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60)
def login_to_site(email: str, site: str):
	"""
	Login to the product site
	"""
	validate_email_address(email, throw=True)
	verified_user = verify_session_user(email)
	if not verified_user:
		frappe.throw(_("Invalid Session"))
	try:
		site_user = frappe.get_doc("Site User", {"user": email, "site": site, "enabled": 1})
		return site_user.login_to_site()
	except frappe.DoesNotExistError:
		frappe.throw(f"User {email} not found in site {site}")
	except Exception as e:
		log_error("Error logging in site", data=e)
		frappe.throw(_("Login failed"))


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def check_session_id():
	"""
	Check if the session id is valid
	"""

	session_id = frappe.local.request.cookies.get("site_user_sid")
	if not session_id or not isinstance(session_id, str):
		return False

	session_user = frappe.db.get_value("Site User Session", {"session_id": session_id}, "user")
	if not session_user:
		return False

	return session_user
