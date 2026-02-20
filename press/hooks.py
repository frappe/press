from press.api.account import get_frappe_io_auth_url

from . import __version__ as app_version

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
app_include_js = [
	"press.bundle.js",
]

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
]

website_redirects = [
	{"source": "/dashboard/f-login", "target": get_frappe_io_auth_url() or "/"},
	{
		"source": "/suspended-site",
		"target": "/api/method/press.api.handle_suspended_site_redirection",
	},
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
	"Site Backup": "press.press.doctype.site_backup.site_backup.get_permission_query_conditions",
	"Site Domain": ("press.press.doctype.site_domain.site_domain.get_permission_query_conditions"),
	"TLS Certificate": "press.press.doctype.tls_certificate.tls_certificate.get_permission_query_conditions",
	"Team": "press.press.doctype.team.team.get_permission_query_conditions",
	"Subscription": ("press.press.doctype.subscription.subscription.get_permission_query_conditions"),
	"Stripe Payment Method": "press.press.doctype.stripe_payment_method.stripe_payment_method.get_permission_query_conditions",
	"Balance Transaction": "press.press.doctype.balance_transaction.balance_transaction.get_permission_query_conditions",
	"Invoice": "press.press.doctype.invoice.invoice.get_permission_query_conditions",
	"App Source": ("press.press.doctype.app_source.app_source.get_permission_query_conditions"),
	"App Release": ("press.press.doctype.app_release.app_release.get_permission_query_conditions"),
	"Release Group": "press.press.doctype.release_group.release_group.get_permission_query_conditions",
	"Deploy Candidate": "press.press.doctype.deploy_candidate.deploy_candidate.get_permission_query_conditions",
	"Deploy Candidate Difference": "press.press.doctype.deploy_candidate_difference.deploy_candidate_difference.get_permission_query_conditions",
	"Deploy": "press.press.doctype.deploy.deploy.get_permission_query_conditions",
	"Bench": "press.press.doctype.bench.bench.get_permission_query_conditions",
	"Server": "press.press.doctype.server.server.get_permission_query_conditions",
	"Database Server": "press.press.doctype.database_server.database_server.get_permission_query_conditions",
	"Virtual Machine": "press.press.doctype.virtual_machine.virtual_machine.get_permission_query_conditions",
	"Press Webhook": "press.press.doctype.press_webhook.press_webhook.get_permission_query_conditions",
	"Press Webhook Log": "press.press.doctype.press_webhook_log.press_webhook_log.get_permission_query_conditions",
	"SQL Playground Log": "press.press.doctype.sql_playground_log.sql_playground_log.get_permission_query_conditions",
	"Site Database User": "press.press.doctype.site_database_user.site_database_user.get_permission_query_conditions",
	"Server Snapshot": "press.press.doctype.server_snapshot.server_snapshot.get_permission_query_conditions",
	"Server Snapshot Recovery": "press.press.doctype.server_snapshot_recovery.server_snapshot_recovery.get_permission_query_conditions",
}
has_permission = {
	"Site": "press.overrides.has_permission",
	"Site Backup": "press.overrides.has_permission",
	"Site Domain": "press.overrides.has_permission",
	"TLS Certificate": "press.overrides.has_permission",
	"Team": "press.press.doctype.team.team.has_permission",
	"Subscription": "press.overrides.has_permission",
	"Stripe Payment Method": "press.overrides.has_permission",
	"Balance Transaction": "press.overrides.has_permission",
	"Invoice": "press.press.doctype.invoice.invoice.has_permission",
	"App Source": "press.overrides.has_permission",
	"App Release": "press.press.doctype.app_release.app_release.has_permission",
	"Release Group": "press.overrides.has_permission",
	"Deploy Candidate": "press.overrides.has_permission",
	"Deploy Candidate Difference": "press.overrides.has_permission",
	"Deploy": "press.overrides.has_permission",
	"Bench": "press.overrides.has_permission",
	"Server": "press.overrides.has_permission",
	"Database Server": "press.overrides.has_permission",
	"Press Webhook": "press.overrides.has_permission",
	"Press Webhook Log": "press.overrides.has_permission",
	"Press Webhook Attempt": "press.press.doctype.press_webhook_attempt.press_webhook_attempt.has_permission",
	"SQL Playground Log": "press.overrides.has_permission",
	"Site Database User": "press.overrides.has_permission",
	"Server Snapshot": "press.overrides.has_permission",
	"Server Snapshot Recovery": "press.overrides.has_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Stripe Webhook Log": {
		"after_insert": [
			"press.press.doctype.invoice.stripe_webhook_handler.handle_stripe_webhook_events",
			"press.press.doctype.team.team.process_stripe_webhook",
		],
	},
	"Address": {"validate": "press.api.billing.validate_gst"},
	"Site": {
		"before_insert": "press.press.doctype.team.team.validate_site_creation",
		"after_insert": "press.press.doctype.press_role.press_role.create_user_resource",
	},
	"Marketplace App Subscription": {
		"on_update": "press.press.doctype.storage_integration_subscription.storage_integration_subscription.create_after_insert",
	},
	"Release Group": {
		"after_insert": "press.press.doctype.press_role.press_role.create_user_resource",
	},
	"Server": {
		"after_insert": "press.press.doctype.press_role.press_role.create_user_resource",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"weekly_long": ["press.press.doctype.marketplace_app.events.auto_review_for_missing_steps"],
	"daily": [
		"press.experimental.doctype.referral_bonus.referral_bonus.credit_referral_bonuses",
		"press.press.doctype.log_counter.log_counter.record_counts",
		"press.press.doctype.incident.incident.notify_ignored_servers",
		"press.press.doctype.database_server.database_server.unindex_mariadb_binlogs",
		"press.press.doctype.database_server.database_server.remove_uploaded_binlogs_from_disk",
		"press.press.doctype.database_server.database_server.remove_uploaded_binlogs_from_s3",
		"press.press.doctype.mariadb_binlog.mariadb_binlog.cleanup_old_records",
		"press.press.doctype.database_server.database_server.delete_mariadb_binlog_for_archived_servers",
		"press.press.doctype.team.team.check_budget_alerts",
		"press.press.doctype.site.site.archive_creation_failed_sites",
	],
	"daily_long": [
		"press.press.audit.check_bench_fields",
		"press.press.audit.check_offsite_backups",
		"press.press.audit.plan_audit",
		"press.press.audit.check_app_server_replica_benches",
		"press.press.doctype.invoice.invoice.finalize_unpaid_prepaid_credit_invoices",
		"press.press.doctype.bench.bench.sync_analytics",
		"press.saas.doctype.saas_app_subscription.saas_app_subscription.suspend_prepaid_subscriptions",
		"press.press.doctype.backup_restoration_test.backup_test.archive_backup_test_sites",
		"press.press.doctype.payout_order.payout_order.create_marketplace_payout_orders",
		"press.press.doctype.root_domain.root_domain.cleanup_cname_records",
		"press.press.doctype.remote_file.remote_file.poll_file_statuses",
		"press.press.doctype.site_domain.site_domain.update_dns_type",
		"press.press.doctype.press_webhook_log.press_webhook_log.clean_logs_older_than_24_hours",
		"press.press.doctype.payment_due_extension.payment_due_extension.remove_payment_due_extension",
		"press.press.doctype.tls_certificate.tls_certificate.notify_custom_tls_renewal",
		"press.press.doctype.site.site.suspend_sites_exceeding_disk_usage_for_last_14_days",
		"press.press.doctype.user_2fa.user_2fa.yearly_2fa_recovery_code_reminder",
		"press.press.doctype.registry_server.registry_server.delete_old_images_from_registry",
		"press.saas.doctype.product_trial_request.product_trial_request.gather_daily_stats",
		"press.press.doctype.agent_job.agent_job.agent_poll_count_stats_daily",
	],
	"hourly": [
		"press.press.doctype.site.backups.cleanup_local",
		"press.press.doctype.agent_job.agent_job.update_job_step_status",
		"press.press.doctype.bench.bench.archive_obsolete_benches",
		"press.press.doctype.site.backups.schedule_logical_backups_for_sites_with_backup_time",
		"press.press.doctype.site.backups.schedule_physical_backups_for_sites_with_backup_time",
		"press.press.doctype.tls_certificate.tls_certificate.renew_tls_certificates",
		"press.saas.doctype.product_trial_request.product_trial_request.expire_long_pending_trial_requests",
		"press.overrides.cleanup_ansible_tmp_files",
		"press.press.doctype.site.site.archive_suspended_sites",
		"press.press.doctype.site.site.send_warning_mail_regarding_sites_exceeding_disk_usage",
		"press.press.doctype.add_on_storage_log.add_on_storage_log.send_disk_extention_notification",
		"press.press.doctype.server_snapshot_recovery.server_snapshot_recovery.expire_backups",
		"press.press.doctype.server_snapshot.server_snapshot.expire_snapshots",
		"press.saas.doctype.product_trial.product_trial.sync_product_site_users",
		"press.press.doctype.database_server.database_server.sync_binlogs_info",
		"press.press.doctype.database_server.database_server.update_database_schema_sizes",
	],
	"hourly_long": [
		"press.press.doctype.release_group.release_group.prune_servers_without_sites",
		"press.press.doctype.release_group.release_group.add_public_servers_to_public_groups",
		"press.press.doctype.server.server.scale_workers",
		"press.press.doctype.usage_record.usage_record.link_unlinked_usage_records",
		"press.press.doctype.bench.bench.sync_benches",
		"press.press.doctype.invoice.invoice.finalize_draft_invoices",
		"press.press.doctype.agent_job.agent_job.fail_old_jobs",
		"press.press.doctype.press_job.press_job.fail_stuck_press_jobs",
		"press.press.doctype.site_update.site_update.mark_stuck_updates_as_fatal",
		"press.press.doctype.deploy_candidate_build.deploy_candidate_build.cleanup_build_directories",
		"press.press.doctype.deploy_candidate_build.deploy_candidate_build.check_builds_status",
		"press.press.doctype.virtual_machine.virtual_machine.snapshot_oci_virtual_machines",
		"press.press.doctype.virtual_machine.virtual_machine.snapshot_hetzner_virtual_machines",
		"press.press.doctype.virtual_machine.virtual_machine.snapshot_aws_internal_virtual_machines",
		"press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.delete_old_snapshots",
		"press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.delete_expired_snapshots",
		"press.press.doctype.app_release.app_release.cleanup_unused_releases",
		"press.press.doctype.press_webhook.press_webhook.auto_disable_high_delivery_failure_webhooks",
		"press.saas.doctype.product_trial_request.product_trial_request.gather_hourly_stats",
		"press.press.doctype.agent_job.agent_job.agent_poll_count_stats_hourly",
		"press.press.doctype.team.team.auto_enable_ssh_access_for_7_days_older_teams",
		"press.press.doctype.database_server.database_server.database_flush_tables_of_public_servers",
	],
	"all": [
		"press.auth.flush",
		"press.press.doctype.site.sync.sync_setup_wizard_status",
		"press.press.doctype.site.archive.archive_suspended_trial_sites",
		"press.press.doctype.agent_job.agent_job.flush",
	],
	"cron": {
		"1-59/2 * * * *": [
			"press.press.doctype.incident.incident.validate_incidents",
		],
		"*/2 * * * *": [
			"press.press.doctype.incident.incident.resolve_incidents",
		],
		"0 4 * * *": [
			"press.press.doctype.site.backups.cleanup_offsite",
			"press.press.doctype.site.backups.expire_physical",
			"press.press.cleanup.unlink_remote_files_from_site",
		],
		"10 0 * * *": [
			"press.press.audit.check_backup_records",
			"press.press.audit.billing_audit",
		],
		"0 3 * * *": [
			"press.press.doctype.drip_email.drip_email.send_drip_emails",
			"press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.sync_all_snapshots_from_aws",
		],
		"* * * * * 0/5": [
			"press.press.doctype.agent_job.agent_job.poll_pending_jobs",
			"press.press.doctype.press_webhook_log.press_webhook_log.process",
			"press.press.doctype.telegram_message.telegram_message.send_telegram_message",
			"press.press.doctype.agent_update.agent_update.process_bulk_agent_update",
			"press.press.doctype.press_job.press_job.process_failed_callbacks",
			"press.press.doctype.server_snapshot_recovery.server_snapshot_recovery.resume_warmed_up_restorations",
			"press.press.doctype.server_snapshot.server_snapshot.move_pending_snapshots_to_processing",
		],
		"* * * * * 0/30": [
			"press.press.doctype.account_request.account_request.expire_request_key",
			"press.press.doctype.physical_backup_restoration.physical_backup_restoration.process_scheduled_restorations",
		],
		"0 */2 * * *": [
			"press.signup_e2e.run_signup_e2e",
		],
		"0 */6 * * *": [
			"press.press.doctype.server.server.cleanup_unused_files",
			"press.press.doctype.razorpay_payment_record.razorpay_payment_record.fetch_pending_payment_orders",
		],
		"*/15 * * * *": [
			"press.press.doctype.site_update.site_update.schedule_updates",
			"press.press.doctype.site.backups.schedule_logical_backups",
			"press.press.doctype.site.backups.schedule_physical_backups",
			"press.press.doctype.site_migration.site_migration.run_scheduled_migrations",
			"press.press.doctype.version_upgrade.version_upgrade.run_scheduled_upgrades",
			"press.press.doctype.subscription.subscription.create_usage_records",
			"press.press.doctype.virtual_machine.virtual_machine.sync_virtual_machines",
			"press.press.doctype.mariadb_stalk.mariadb_stalk.fetch_stalks",
			"press.press.doctype.virtual_machine.virtual_machine.rolling_snapshot_database_server_virtual_machines",
			"press.infrastructure.doctype.virtual_disk_resize.virtual_disk_resize.run_scheduled_resizes",
		],
		"*/5 * * * *": [
			"press.press.doctype.version_upgrade.version_upgrade.update_from_site_update",
			"press.press.doctype.site_replication.site_replication.update_from_site",
			"press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.sync_snapshots",
			"press.press.doctype.site.site.sync_sites_setup_wizard_complete_status",
			"press.press.doctype.drip_email.drip_email.send_welcome_email",
			"press.press.doctype.site_update.site_update.run_scheduled_updates",
			"press.press.doctype.virtual_machine.virtual_machine.snapshot_aws_servers",
			"press.press.doctype.app.app.poll_new_releases",
			"press.utils.jobs.alert_on_zombie_rq_jobs",
			"press.saas.doctype.product_trial.product_trial.replenish_standby_sites",
			"press.press.doctype.server_plan.server_plan.sync_machine_availability_status_of_plans",
		],
		"* * * * *": [
			"press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.sync_physical_backup_snapshots",
			"press.press.doctype.deploy_candidate_build.deploy_candidate_build.run_scheduled_builds",
			"press.press.doctype.agent_request_failure.agent_request_failure.remove_old_failures",
			"press.saas.doctype.site_access_token.site_access_token.cleanup_expired_access_tokens",
			"press.press.doctype.server_snapshot.server_snapshot.sync_ongoing_server_snapshots",
			"press.press.doctype.site.site.create_subscription_for_trial_sites",
			"press.press.doctype.monitor_server.monitor_server.check_monitoring_servers_rate_limit_key",
			"press.press.doctype.auto_scale_record.auto_scale_record.run_scheduled_scale_records",
		],
		"*/10 * * * *": [
			"press.press.doctype.site.saas_pool.create",
			"press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot.sync_rolling_snapshots",
			"press.press.doctype.database_server.database_server.auto_purge_binlogs_by_size_limit",
		],
		"*/30 * * * *": [
			"press.press.doctype.site_update.scheduled_auto_updates.trigger",
			"press.press.doctype.team.suspend_sites.execute",
		],
		"15,45 * * * *": [
			"press.press.doctype.site.site_usages.update_cpu_usages",
			"press.press.doctype.site.site_usages.update_disk_usages",
		],
		"15 2,4 * * *": [
			"press.press.doctype.team_deletion_request.team_deletion_request.process_team_deletion_requests",
		],
		"0 0 1 */3 *": ["press.press.doctype.backup_restoration_test.backup_test.run_backup_restore_test"],
		"0 8 * * *": [
			"press.press.doctype.aws_savings_plan_recommendation.aws_savings_plan_recommendation.create",
			"press.press.cleanup.reset_large_output_fields_from_ansible_tasks",
		],
		"0 21 * * *": [
			"press.press.audit.partner_billing_audit",
		],
		"0 6 * * *": [
			"press.press.audit.suspend_sites_with_disabled_team",
			"press.press.doctype.tls_certificate.tls_certificate.retrigger_failed_wildcard_tls_callbacks",
			"press.press.doctype.aws_savings_plan_recommendation.aws_savings_plan_recommendation.refresh",
			"press.infrastructure.doctype.ssh_access_audit.ssh_access_audit.run",
		],
		"0 9 * * 2": [
			"press.press.doctype.build_metric.build_metric.create_build_metric",
			"press.saas.doctype.product_trial_request.product_trial_request.gather_weekly_stats",
		],
	},
}

deploy_hours = [1, 2, 3, 4, 5, 21, 22, 23]  # Purposefully avoiding 0

fixtures = [
	"Agent Job Type",
	"Press Job Type",
	"Frappe Version",
	"MariaDB Variable",
	"Cloud Region",
	{"dt": "Role", "filters": [["role_name", "like", "Press%"]]},
	"Site Config Key Blacklist",
	"Press Method Permission",
	"Bench Dependency",
	"Server Storage Plan",
	"Server Snapshot Plan",
	"Press Webhook Event",
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
# on_logout = "press.overrides.on_logout"
on_login = "press.overrides.on_login"

before_request = "press.overrides.before_request"
before_job = "press.overrides.before_job"
# after_job = "press.overrides.after_job"

# Data Deletion Privacy Docs

user_data_fields = [
	{"doctype": "Team", "strict": True},
]

auth_hooks = ["press.auth.hook"]

page_renderer = ["press.metrics.MetricsRenderer"]

export_python_type_annotations = True

default_log_clearing_doctypes = {
	"Alertmanager Webhook Log": 60,
}


# These are used for some business logic, they should be manually evicted.
__persistent_cache_keys = [
	"agent-jobs",
	"monitor-transactions",
	"google_oauth_flow*",
	"fc_oauth_state*",
	"one_time_login_key*",
	"press-auth-logs",
	"rl:*",
]

# `frappe.rename_doc` erases all caches, this hook preserves some of them.
# Note:
# - These are only "most used" cache keys. This lessens the impact of renames but doesn't eliminate them.
# - Adding more keys here will slow down `frappe.clear_cache` but it's "rare" enough.
# - This also means that other "valid" frappe.clear_cache() usage won't clear these keys!
# - Use frappe.cache.flushall() instead.
persistent_cache_keys = [
	*__persistent_cache_keys,
	"agent_job_step_output",
	"all_apps",
	"app_hooks",
	"assets_json",
	"assignment_rule_map",
	"bootinfo",
	"builder.builder*",  # path resolution, it has its own cache eviction.
	"db_tables",
	"defaults",
	"doctype_form_meta",
	"doctype_meta",
	"doctypes_with_web_view",
	"document_cache::*",
	"document_naming_rule_map",
	"domain_restricted_doctypes",
	"domain_restricted_pages",
	"energy_point_rule_map",
	"frappe.utils.scheduler.schedule_jobs_based_on_activity*",  # dormant checks
	"frappe.website.page_renderers*",  # FW's routing
	"home_page",
	"information_schema:counts",
	"installed_app_modules",
	"ip_country_map",
	"is_table",
	"languages",
	"last_db_session_update",
	"marketplace_apps",
	"merged_translations",
	"metadata_version",
	"server_script_map",  # Routing and actual server scripts
	"session",
	"table_columns",
	"website_page",
	"website_route_rules",
]

before_migrate = ["press.overrides.before_after_migrate"]
after_migrate = ["press.overrides.before_after_migrate"]
