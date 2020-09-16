# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

keys_used_in_frappe = [
	"admin_password",
	"allow_tests",
	"always_use_account_email_id_as_sender",
	"always_use_account_name_as_sender_name",
	"auto_email_id",
	"converted_rupee_to_paisa",
	"data_import_batch_size",
	"db_host",
	"db_name",
	"db_password",
	"db_port",
	"db_ssl_ca",
	"db_ssl_cert",
	"db_ssl_key",
	"db_type",
	"deny_multiple_sessions",
	"developer_mode",
	"disable_async",
	"disable_error_snapshot",
	"disable_global_search",
	"disable_scheduler",
	"disable_session_cache",
	"disable_website_cache",
	"dropbox_access_key",
	"dropbox_broker_site",
	"dropbox_secret_key",
	"email_sender_name",
	"error_report_email",
	"frappecloud_url",
	"google_analytics_id",
	"host_name",
	"http_port",
	"ignore_csrf",
	"in_test",
	"install_apps",
	"keep_backups_for_hours",
	"local_infile",
	"logging",
	"mail_login",
	"mail_password",
	"mail_port",
	"mail_server",
	"mixpanel_id",
	"monitor",
	"pause_scheduler",
	"paypal_password",
	"paypal_signature",
	"paypal_username",
	"pop_timeout",
	"rate_limit",
	"rds_db",
	"restart_supervisor_on_update",
	"restart_systemd_on_update",
	"root_login",
	"root_password",
	"sandbox_api_key",
	"sandbox_api_password",
	"sandbox_api_secret",
	"sandbox_api_username",
	"sandbox_publishable_key",
	"sandbox_signature",
	"server_script_enabled",
	"skip_setup_wizard",
	"socketio_port",
	"use_ssl",
	"use_tls",
	"webserver_port",
	"hub_url",
]

keys_used_in_erpnext = [
	"plaid_client_id",
	"plaid_env",
	"plaid_public_key",
	"plaid_secret",
]


class SiteConfig(Document):
	def get_type(self):
		return frappe.db.get_value("Site Config Key", self.key, "type")
