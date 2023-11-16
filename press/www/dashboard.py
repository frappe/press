# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe

base_template_path = "templates/www/dashboard.html"
no_cache = 1


def get_context():
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
		press_frontend_sentry_dsn=frappe.conf.press_frontend_sentry_dsn or '',
		press_frontend_posthog_host=frappe.conf.posthog_host or '',
		press_frontend_posthog_project_id=frappe.conf.posthog_project_id or '',
		press_site_name=frappe.conf.site,
		site_name=frappe.local.site,
	)
