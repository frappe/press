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
app_license = "Proprietary"
version = app_version
home_page = "index"

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

# Installation
# ------------

# before_install = "press.install.before_install"
# after_install = "press.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "press.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Site": "press.press.doctype.site.site.get_permission_query_conditions",
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
			"press.press.doctype.payment.payment.process_stripe_webhook",
			"press.press.doctype.subscription.subscription.process_stripe_webhook",
		],
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"hourly": ["press.press.doctype.frappe_app.frappe_app.poll_new_releases"],
	"hourly_long": [
		"press.press.doctype.site_usage_ledger_entry.site_usage_ledger_entry.create_ledger_entries",
		"press.press.doctype.site_usage_ledger_entry.site_usage_ledger_entry.create_usage_record_for_failed_requests",
	],
	"cron": {
		"* * * * * 0/5": ["press.press.doctype.agent_job.agent_job.poll_pending_jobs"],
		"* * * * * 0/60": [
			"press.press.doctype.agent_job.agent_job.collect_site_uptime",
			"press.press.doctype.agent_job.agent_job.collect_site_analytics",
		],
		"*/60 * * * *": ["press.press.doctype.agent_job.agent_job.schedule_backups"],
	},
}

fixtures = ["Agent Job Type", "Plan"]
# Testing
# -------

# before_tests = "press.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "press.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "press.task.get_dashboard_data"
# }
