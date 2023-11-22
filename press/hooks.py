# -*- coding: utf-8 -*-
from . import __version__ as app_version
from press.api.account import get_frappe_io_auth_url

app_name = "press"
app_title = "Press"
app_publisher = "Frappe"
app_description = "Managed Frappe Hosting"
app_icon = "octicon octicon-rocket"
app_color = "grey"
app_email = "aditya@frappe.io"
app_license = "GNU Affero General Public License v3.0"
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

website_route_rules = [
	{"from_route": "/dashboard/<path:app_path>", "to_route": "dashboard"},
	{"from_route": "/dashboard2/<path:app_path>", "to_route": "dashboard2"},
]

website_redirects = [
	{"source": "/dashboard/f-login", "target": get_frappe_io_auth_url() or "/"},
	{"source": "/f-login", "target": "/dashboard/f-login"},
	{"source": "/signup", "target": "/erpnext/signup"},
]

email_css = ["/assets/press/css/email.css"]

jinja = {
	"filters": ["press.press.doctype.marketplace_app.utils.number_k_format"],
	"methods": ["press.utils.get_country_info"],
}

# Installation
# ------------

# before_install = "press.install.before_install"
after_install = "press.install.after_install"
after_migrate = ["press.api.account.clear_country_list_cache", "press.sanity.checks"]

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

notification_config = "press.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Site": "press.press.doctype.site.site.get_permission_query_conditions",
	"Site Domain": (
		"press.press.doctype.site_domain.site_domain.get_permission_query_conditions"
	),
	"TLS Certificate": "press.press.doctype.tls_certificate.tls_certificate.get_permission_query_conditions",
	"Team": "press.press.doctype.team.team.get_permission_query_conditions",
	"Subscription": (
		"press.press.doctype.subscription.subscription.get_permission_query_conditions"
	),
	"Stripe Payment Method": "press.press.doctype.stripe_payment_method.stripe_payment_method.get_permission_query_conditions",
	"Balance Transaction": "press.press.doctype.balance_transaction.balance_transaction.get_permission_query_conditions",
	"Invoice": "press.press.doctype.invoice.invoice.get_permission_query_conditions",
	"App Source": (
		"press.press.doctype.app_source.app_source.get_permission_query_conditions"
	),
	"App Release": (
		"press.press.doctype.app_release.app_release.get_permission_query_conditions"
	),
	"Release Group": "press.press.doctype.release_group.release_group.get_permission_query_conditions",
	"Deploy Candidate": "press.press.doctype.deploy_candidate.deploy_candidate.get_permission_query_conditions",
	"Deploy Candidate Difference": "press.press.doctype.deploy_candidate_difference.deploy_candidate_difference.get_permission_query_conditions",
	"Deploy": "press.press.doctype.deploy.deploy.get_permission_query_conditions",
	"Bench": "press.press.doctype.bench.bench.get_permission_query_conditions",
	"Server": "press.press.doctype.server.server.get_permission_query_conditions",
	"Database Server": "press.press.doctype.database_server.database_server.get_permission_query_conditions",
	"Virtual Machine": "press.press.doctype.virtual_machine.virtual_machine.get_permission_query_conditions",
}
has_permission = {
	"Site": "press.overrides.has_permission",
	"Site Domain": "press.overrides.has_permission",
	"TLS Certificate": "press.overrides.has_permission",
	"Team": "press.press.doctype.team.team.has_permission",
	"Subscription": "press.overrides.has_permission",
	"Stripe Payment Method": "press.overrides.has_permission",
	"Balance Transaction": "press.overrides.has_permission",
	"Invoice": "press.overrides.has_permission",
	"App Source": "press.overrides.has_permission",
	"App Release": "press.press.doctype.app_release.app_release.has_permission",
	"Release Group": "press.overrides.has_permission",
	"Deploy Candidate": "press.overrides.has_permission",
	"Deploy Candidate Difference": "press.overrides.has_permission",
	"Deploy": "press.overrides.has_permission",
	"Bench": "press.overrides.has_permission",
	"Server": "press.overrides.has_permission",
	"Database Server": "press.overrides.has_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Stripe Webhook Log": {
		"after_insert": [
			"press.press.doctype.invoice.stripe_webhook_handler.handle_stripe_invoice_webhook_events",
			"press.press.doctype.team.team.process_stripe_webhook",
		],
	},
	"Address": {"validate": "press.api.billing.validate_gst"},
	"Site": {"before_insert": "press.press.doctype.team.team.validate_site_creation"},
	"Marketplace App Subscription": {
		"on_update": "press.press.doctype.storage_integration_subscription.storage_integration_subscription.create_after_insert",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"press.press.doctype.tls_certificate.tls_certificate.renew_tls_certificates",
		"press.experimental.doctype.referral_bonus.referral_bonus.credit_referral_bonuses",
	],
	"daily_long": [
		"press.press.audit.check_bench_fields",
		"press.press.audit.check_offsite_backups",
		"press.press.audit.check_backup_records",
		"press.press.audit.check_app_server_replica_benches",
		"press.press.doctype.invoice.invoice.finalize_unpaid_prepaid_credit_invoices",
		"press.press.doctype.bench.bench.sync_analytics",
		"press.saas.doctype.saas_app_subscription.saas_app_subscription.suspend_prepaid_subscriptions",
		"press.press.doctype.payout_order.payout_order.create_marketplace_payout_orders",
		"press.press.doctype.root_domain.root_domain.cleanup_cname_records",
		"press.press.doctype.virtual_machine.virtual_machine.snapshot_virtual_machines",
		"press.press.doctype.remote_file.remote_file.poll_file_statuses",
	],
	"hourly": [
		"press.press.doctype.site.backups.cleanup_local",
	],
	"hourly_long": [
		"press.press.doctype.server.server.scale_workers",
		"press.press.doctype.subscription.subscription.create_usage_records",
		"press.press.doctype.usage_record.usage_record.link_unlinked_usage_records",
		"press.press.doctype.bench.bench.sync_benches",
		"press.press.doctype.invoice.invoice.finalize_draft_invoices",
		"press.press.doctype.app.app.poll_new_releases",
		"press.press.doctype.agent_job.agent_job.fail_old_jobs",
		"press.press.doctype.site_update.site_update.mark_stuck_updates_as_fatal",
		"press.press.doctype.deploy_candidate.deploy_candidate.cleanup_build_directories",
		"press.press.doctype.deploy_candidate.deploy_candidate.delete_draft_candidates",
		"press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.delete_old_snapshots",
		"press.press.doctype.app_release.app_release.cleanup_unused_releases",
	],
	"all": [
		"press.auth.flush",
	],
	"cron": {
		"0 4 * * *": [
			"press.press.doctype.site.backups.cleanup_offsite",
			"press.press.cleanup.unlink_remote_files_from_site",
			"press.press.audit.check_unbilled_subscriptions",
		],
		"0 3 * * *": [
			"press.press.doctype.drip_email.drip_email.send_drip_emails",
		],
		"* * * * * 0/5": ["press.press.doctype.agent_job.agent_job.poll_pending_jobs"],
		"0 */6 * * *": [
			"press.press.doctype.server.server.cleanup_unused_files",
			"press.press.doctype.razorpay_payment_record.razorpay_payment_record.fetch_pending_payment_orders",
		],
		"30 * * * *": ["press.press.doctype.agent_job.agent_job.suspend_sites"],
		"*/15 * * * *": [
			"press.press.doctype.site_update.site_update.schedule_updates",
			"press.press.doctype.drip_email.drip_email.send_welcome_email",
			"press.press.doctype.site.backups.schedule",
			"press.press.doctype.site_migration.site_migration.run_scheduled_migrations",
			"press.press.doctype.version_upgrade.version_upgrade.run_scheduled_upgrades",
			"press.press.doctype.bench.bench.archive_obsolete_benches",
			"press.press.doctype.subscription.subscription.create_usage_records",
			"press.press.doctype.virtual_machine.virtual_machine.sync_virtual_machines",
		],
		"*/5 * * * *": [
			"press.press.doctype.version_upgrade.version_upgrade.update_from_site_update",
			"press.press.doctype.site_replication.site_replication.update_from_site",
			"press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.sync_snapshots",
		],
		"* * * * *": [
			"press.press.doctype.deploy_candidate.deploy_candidate.run_scheduled_builds",
		],
		"*/10 * * * *": [
			"press.saas.doctype.saas_product.pooling.create",
			"press.press.doctype.site.saas_pool.create",
		],
		"*/30 * * * *": ["press.press.doctype.site_update.scheduled_auto_updates.trigger"],
		"15,45 * * * *": [
			"press.press.doctype.site.site_usages.update_cpu_usages",
			"press.press.doctype.site.site_usages.update_disk_usages",
		],
		"15 2,4 * * *": [
			"press.press.doctype.team_deletion_request.team_deletion_request.process_team_deletion_requests",
		],
		"0 0 1 */3 *": [
			"press.press.doctype.backup_restoration_test.backup_test.run_backup_restore_test"
		],
		"*/30 * 11 * *": ["press.press.doctype.team.suspend_sites.execute"],
	},
}

deploy_hours = [1, 2, 3, 4]

fixtures = [
	"Agent Job Type",
	"Press Job Type",
	"Frappe Version",
	"MariaDB Variable",
	"Cloud Region",
	"Plan",
	{"dt": "Role", "filters": [["role_name", "like", "Press%"]]},
	"Site Config Key Blacklist",
	"Press Method Permission",
	"Bench Dependency",
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

override_doctype_class = {"User": "press.overrides.CustomUser"}

on_session_creation = "press.overrides.on_session_creation"
on_logout = "press.overrides.on_logout"


# Data Deletion Privacy Docs

user_data_fields = [
	{"doctype": "Team", "strict": True},
]

auth_hooks = ["press.auth.hook"]
