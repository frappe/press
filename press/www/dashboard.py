# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe.utils.caching import redis_cache

from press.utils import (
	chat_enabled,
	get_default_team_for_user,
	get_valid_teams_for_user,
)
from press.utils.user import is_beta_tester, is_desk_user, is_system_manager

base_template_path = "templates/www/dashboard.html"
no_cache = 1


def get_context():
	return _get_context()


def _get_context():
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context = frappe._dict()
	context.boot = get_boot()
	context.boot.csrf_token = csrf_token
	return context


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw("This method is only meant for developer mode")
	return get_boot()


def get_boot():
	return frappe._dict(
		frappe_version=frappe.__version__,
		press_dashboard_sentry_dsn=frappe.conf.press_dashboard_sentry_dsn or "",
		press_frontend_posthog_host=frappe.conf.posthog_host or "",
		press_frontend_posthog_project_id=frappe.conf.posthog_project_id or "",
		press_site_name=frappe.conf.site,
		site_name=frappe.local.site,
		default_team=get_default_team_for_user(frappe.session.user),
		valid_teams=get_valid_teams_for_user(frappe.session.user),
		chat_enabled=chat_enabled(),
		is_system_user=frappe.session.data.user_type == "System User",
		verify_cards_with_micro_charge=frappe.db.get_single_value(
			"Press Settings", "verify_cards_with_micro_charge"
		),
		**(
			frappe.db.get_values(
				"Press Settings",
				"Press Settings",
				[
					"free_credits_inr",
					"free_credits_usd",
					"chat_base_url",
					"chat_website_token",
					"chat_support_start_time",
					"chat_support_end_time",
				],
				as_dict=True,
			)[0]
		),
		user=get_user(),
	)


@redis_cache(user=True, ttl=60 * 5)
def get_user():
	user = frappe.session.user
	full_name, email = frappe.get_value("User", user, ["full_name", "email"])
	return {
		"id": frappe.session.user,
		"name": full_name,
		"email": email,
		"is_system_manager": is_system_manager(user),
		"is_desk_user": is_desk_user(user),
		"is_beta_tester": is_beta_tester(),
	}
