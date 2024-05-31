# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from press.utils import get_default_team_for_user, get_valid_teams_for_user

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
		press_frontend_sentry_dsn=frappe.conf.press_frontend_sentry_dsn or "",
		press_dashboard_sentry_dsn=frappe.conf.press_dashboard_sentry_dsn or "",
		press_frontend_posthog_host=frappe.conf.posthog_host or "",
		press_frontend_posthog_project_id=frappe.conf.posthog_project_id or "",
		press_site_name=frappe.conf.site,
		site_name=frappe.local.site,
		default_team=get_default_team_for_user(frappe.session.user),
		valid_teams=get_valid_teams_for_user(frappe.session.user),
		is_system_user=frappe.session.data.user_type == "System User",
		verify_cards_with_micro_charge=frappe.db.get_single_value(
			"Press Settings", "verify_cards_with_micro_charge"
		),
		**(
			frappe.db.get_values(
				"Press Settings",
				"Press Settings",
				["free_credits_inr", "free_credits_usd"],
				as_dict=True,
			)[0]
		),
	)
