# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "press"
app_title = "Press"
app_publisher = "Frappe"
app_description = "Managed Frappe Hosting"
app_icon = "octicon octicon-rocket"
app_color = "grey"
app_email = "aditya@erpnext.com"
app_license = "MIT"
version = app_version

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/press/css/press.css"
# app_include_js = "/assets/press/js/press.js"

# include js, css files in header of web template
# web_include_css = "/assets/press/css/press.css"
# web_include_js = "/assets/press/js/press.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "press.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

look_for_sidebar_json = True

base_template_map = {
	r"docs.*": "templates/doc.html",
	r"internal.*": "templates/doc.html",
}

update_website_context = ["press.overrides.update_website_context"]

# Installation
# ------------

# before_install = "press.install.before_install"
after_install = "press.install.after_install"
after_migrate = "press.api.account.clear_country_list_cache"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "press.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Site": "press.press.doctype.site.site.get_permission_query_conditions",
	"Frappe App": (
		"press.press.doctype.frappe_app.frappe_app.get_permission_query_conditions"
	),
}
# has_permission = {
# 	"Site": "press.press.doctype.site.site.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Stripe Webhook Log": {
		"after_insert": [
			"press.press.doctype.invoice.invoice.process_stripe_webhook",
			"press.press.doctype.team.team.process_stripe_webhook",
		],
	},
	"Address": {"validate": "press.api.billing.validate_gst"},
	"Site": {"after_insert": "press.press.doctype.team.team.update_site_onboarding"},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"press.press.cleanup.remove_logs",
		"press.press.doctype.team.suspend_sites.execute",
		"press.press.doctype.tls_certificate.tls_certificate.renew_tls_certificates",
		"press.press.doctype.invoice.invoice.submit_invoices",
	],
	"hourly": ["press.press.doctype.frappe_app.frappe_app.poll_new_releases"],
	"hourly_long": [
		"press.press.doctype.bench.bench.archive_obsolete_benches",
		"press.press.doctype.bench.bench.scale_workers",
		"press.press.doctype.agent_job.agent_job.schedule_backups",
		"press.press.doctype.subscription.subscription.create_usage_records",
		"press.press.doctype.bench.bench.sync_benches",
		"press.press.doctype.site.site_usages.update_cpu_usages",
	],
	"cron": {
		"0 3 * * *": ["press.press.doctype.remote_file.remote_file.poll_file_statuses"],
		"0 4 * * *": [
			"press.press.cleanup.cleanup_backups",
			"press.press.cleanup.remove_baggage",
		],
		"* * * * * 0/5": ["press.press.doctype.agent_job.agent_job.poll_pending_jobs"],
		"* * * * * 0/60": [
			"press.press.doctype.agent_job.agent_job.collect_site_uptime",
			"press.press.doctype.agent_job.agent_job.collect_site_analytics",
			"press.press.doctype.agent_job.agent_job.report_site_downtime",
		],
		"* * * * * 0/30": ["press.press.doctype.agent_job.agent_job.collect_server_status"],
		"0 */6 * * *": ["press.press.doctype.server.server.cleanup_unused_files"],
		"30 * * * *": ["press.press.doctype.agent_job.agent_job.suspend_sites"],
		"*/15 * * * *": [
			"press.press.doctype.site_update.site_update.schedule_updates",
			"press.press.doctype.site.site_usages.update_disk_usages",
		],
	},
}

deploy_hours = [1, 2, 3, 4]

fixtures = [
	"Agent Job Type",
	{"dt": "Role", "filters": [["role_name", "like", "Press%"]]},
	"Print Format",
	"Site Config Key",
	"Site Config Key Blacklist",
]
# Testing
# -------

before_tests = "press.tests.before_test.execute"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {"upload_file": "press.overrides.upload_file"}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "press.task.get_dashboard_data"
# }

on_session_creation = "press.overrides.on_session_creation"
