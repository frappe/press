# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe

base_template_path = "templates/www/dashboard.html"
no_cache = 1


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()
	context.csrf_token = csrf_token
	context.press_frontend_sentry_dsn = frappe.get_conf().press_frontend_sentry_dsn
	context.press_frontend_posthog_host = frappe.conf.get("posthog_host")
	context.press_frontend_posthog_project_id = frappe.conf.get("posthog_project_id")
	context.press_site_name = frappe.conf.get("default_site")
