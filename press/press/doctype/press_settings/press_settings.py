# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import boto3
import frappe
from boto3.session import Session
from frappe.model.document import Document
from frappe.utils import get_url, validate_email_address
from twilio.rest import Client

from press.api.billing import get_stripe
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.telegram_utils import Telegram


class PressSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.app_group.app_group import AppGroup
		from press.press.doctype.erpnext_app.erpnext_app import ERPNextApp

		agent_github_access_token: DF.Data | None
		agent_repository_owner: DF.Data | None
		agent_sentry_dsn: DF.Data | None
		app_include_script: DF.Data | None
		asset_store_access_key: DF.Data | None
		asset_store_bucket_name: DF.Data | None
		asset_store_endpoint: DF.Data | None
		asset_store_region: DF.Data | None
		asset_store_secret_access_key: DF.Password | None
		auto_update_queue_size: DF.Int
		autoscale_discount: DF.Float
		aws_access_key_id: DF.Data | None
		aws_s3_bucket: DF.Data | None
		aws_secret_access_key: DF.Password | None
		backup_interval: DF.Int
		backup_limit: DF.Int
		backup_offset: DF.Int
		backup_region: DF.Data | None
		backup_rotation_scheme: DF.Literal["FIFO", "Grandfather-father-son"]
		bench_configuration: DF.Code
		branch: DF.Data | None
		build_directory: DF.Data | None
		build_server: DF.Link | None
		central_migration_server: DF.Link | None
		certbot_directory: DF.Data
		clone_directory: DF.Data | None
		cluster: DF.Link | None
		code_server: DF.Data | None
		code_server_password: DF.Data | None
		commission: DF.Float
		compress_app_cache: DF.Check
		cool_off_period: DF.Int
		data_40: DF.Data | None
		default_apps: DF.Table[AppGroup]
		default_outgoing_id: DF.Data | None
		default_outgoing_pass: DF.Data | None
		default_server_plan_type: DF.Link | None
		deploy_marker: DF.Data | None
		disable_agent_job_deduplication: DF.Check
		disable_auto_retry: DF.Check
		disable_binlog_indexer_service: DF.Check
		disable_frappe_auth: DF.Check
		disable_physical_backup: DF.Check
		disallow_disposable_emails: DF.Check
		docker_registry_namespace: DF.Data | None
		docker_registry_password: DF.Data | None
		docker_registry_url: DF.Data | None
		docker_registry_username: DF.Data | None
		docker_s3_access_key: DF.Data | None
		docker_s3_secret_key: DF.Password | None
		domain: DF.Link | None
		drive_resource_link: DF.Data | None
		eff_registration_email: DF.Data
		email_recipients: DF.SmallText | None
		enable_app_grouping: DF.Check
		enable_email_pre_verification: DF.Check
		enable_google_oauth: DF.Check
		enable_server_snapshot_recovery: DF.Check
		enable_site_pooling: DF.Check
		enable_spam_check: DF.Check
		enforce_storage_limits: DF.Check
		erpnext_api_key: DF.Data | None
		erpnext_api_secret: DF.Password | None
		erpnext_apps: DF.Table[ERPNextApp]
		erpnext_cluster: DF.Link | None
		erpnext_domain: DF.Link | None
		erpnext_group: DF.Link | None
		erpnext_plan: DF.Link | None
		erpnext_url: DF.Data | None
		execute_incident_action: DF.Check
		frappe_url: DF.Data | None
		frappeio_api_key: DF.Data | None
		frappeio_api_secret: DF.Password | None
		free_credits_inr: DF.Currency
		free_credits_usd: DF.Currency
		github_access_token: DF.Data | None
		github_app_client_id: DF.Data | None
		github_app_client_secret: DF.Data | None
		github_app_id: DF.Data | None
		github_app_private_key: DF.Code | None
		github_app_public_link: DF.Data | None
		github_pat_token: DF.Data | None
		github_webhook_secret: DF.Data | None
		gst_percentage: DF.Float
		hybrid_cluster: DF.Link | None
		hybrid_domain: DF.Link | None
		ic_key: DF.Password | None
		log_server: DF.Link | None
		mailgun_api_key: DF.Data | None
		max_allowed_screenshots: DF.Int
		max_concurrent_physical_restorations: DF.Int
		max_failed_backup_attempts_in_a_day: DF.Int
		micro_debit_charge_inr: DF.Currency
		micro_debit_charge_usd: DF.Currency
		minimum_rebuild_memory: DF.Int
		monitor_server: DF.Link | None
		monitor_token: DF.Data | None
		ngrok_auth_token: DF.Data | None
		npo_discount: DF.Float
		offsite_backups_access_key_id: DF.Data | None
		offsite_backups_count: DF.Int
		offsite_backups_provider: DF.Literal["AWS S3"]
		offsite_backups_secret_access_key: DF.Password | None
		partnership_fee_inr: DF.Int
		partnership_fee_usd: DF.Int
		paypal_enabled: DF.Check
		plausible_api_key: DF.Password | None
		plausible_site_id: DF.Data | None
		plausible_url: DF.Data | None
		press_monitoring_password: DF.Password | None
		press_trial_plan: DF.Link | None
		print_format: DF.Data | None
		publish_docs: DF.Check
		razorpay_key_id: DF.Data | None
		razorpay_key_secret: DF.Password | None
		razorpay_webhook_secret: DF.Data | None
		realtime_job_updates: DF.Check
		redis_cache_size: DF.Int
		remote_access_key_id: DF.Data | None
		remote_link_expiry: DF.Int
		remote_secret_access_key: DF.Password | None
		remote_uploads_bucket: DF.Data | None
		root_domain: DF.Data | None
		rsa_key_size: DF.Literal["2048", "3072", "4096"]
		school_api_key: DF.Data | None
		school_api_secret: DF.Password | None
		school_url: DF.Data | None
		send_email_notifications: DF.Check
		send_telegram_notifications: DF.Check
		servers_using_alternative_http_port_for_communication: DF.SmallText | None
		set_redis_password: DF.Check
		shared_directory: DF.Data | None
		spaces_domain: DF.Link | None
		spamd_api_key: DF.Data | None
		spamd_api_secret: DF.Password | None
		spamd_endpoint: DF.Data | None
		ssh_certificate_authority: DF.Link | None
		staging_expiry: DF.Int
		staging_plan: DF.Link | None
		standby_pool_size: DF.Int
		standby_queue_size: DF.Int
		stripe_inr_plan_id: DF.Data | None
		stripe_product_id: DF.Data | None
		stripe_publishable_key: DF.Data | None
		stripe_secret_key: DF.Password | None
		stripe_usd_plan_id: DF.Data | None
		stripe_webhook_endpoint_id: DF.Data | None
		stripe_webhook_secret: DF.Data | None
		suspend_builds: DF.Check
		telegram_alert_chat_id: DF.Data | None
		telegram_alerts_chat_group: DF.Link | None
		telegram_bot_token: DF.Data | None
		telegram_chat_id: DF.Data | None
		threshold: DF.Float
		tls_renewal_queue_size: DF.Int
		trial_sites_count: DF.Int
		twilio_account_sid: DF.Data | None
		twilio_api_key_secret: DF.Password | None
		twilio_api_key_sid: DF.Data | None
		twilio_phone_number: DF.Phone | None
		usage_record_creation_batch_size: DF.Int
		usd_rate: DF.Float
		use_agent_job_callbacks: DF.Check
		use_app_cache: DF.Check
		use_asset_store: DF.Check
		use_delta_builds: DF.Check
		use_staging_ca: DF.Check
		verify_cards_with_micro_charge: DF.Literal["No", "Only INR", "Only USD", "Both INR and USD"]
		wazuh_server: DF.Data | None
		webroot_directory: DF.Data | None
	# end: auto-generated types

	dashboard_fields = (
		"partnership_fee_inr",
		"partnership_fee_usd",
	)

	def validate(self):
		if self.max_concurrent_physical_restorations > 5:
			frappe.throw("Max Concurrent Physical Restorations should be less than 5")

		if self.send_email_notifications:
			if self.email_recipients:
				# Split the comma-separated emails into a list
				email_list = [email.strip() for email in self.email_recipients.split(",")]
				for email in email_list:
					if not validate_email_address(email):
						frappe.throw(f"Invalid email address: {email}")
			else:
				frappe.throw("Email Recipients List can not be empty")

		if self.minimum_rebuild_memory < 2:
			frappe.throw("Minimum rebuild memory needs to be 2 GB or more.")

	@frappe.whitelist()
	def create_stripe_webhook(self):
		stripe = get_stripe()
		url = frappe.utils.get_url(
			"/api/method/press.press.doctype.stripe_webhook_log.stripe_webhook_log.stripe_webhook_handler"
		)
		webhook = stripe.WebhookEndpoint.create(
			url=url,
			enabled_events=[
				"payment_intent.requires_action",
				"payment_intent.payment_failed",
				"payment_intent.succeeded",
				"payment_method.attached",
				"invoice.payment_action_required",
				"invoice.payment_succeeded",
				"invoice.payment_failed",
				"invoice.finalized",
				"mandate.updated",
				"setup_intent.succeeded",
			],
		)
		self.stripe_webhook_endpoint_id = webhook["id"]
		self.stripe_webhook_secret = webhook["secret"]
		self.flags.ignore_mandatory = True
		self.save()

	@frappe.whitelist()
	def get_github_app_manifest(self):
		if frappe.conf.developer_mode:
			app_name = f"Frappe Cloud {frappe.generate_hash(length=6).upper()}"
		else:
			app_name = "Frappe Cloud"
		return {
			"name": app_name,
			"url": "https://frappe.cloud",
			"hook_attributes": {"url": get_url("api/method/press.api.github.hook")},
			"redirect_url": get_url("github/redirect"),
			"description": "Managed Frappe Hosting",
			"public": True,
			"default_events": ["create", "push", "release"],
			"default_permissions": {"contents": "read"},
			# These keys aren't documented under the app creation from manifest
			# https://docs.github.com/en/free-pro-team@latest/developers/apps/creating-a-github-app-from-a-manifest
			# But are shown under app creation using url parameters
			# https://docs.github.com/en/free-pro-team@latest/developers/apps/creating-a-github-app-using-url-parameters
			# They seem to work. This might change later
			"callback_url": get_url("github/authorize"),
			"request_oauth_on_install": True,
			"setup_on_update": True,
		}

	@property
	def boto3_offsite_backup_session(self) -> Session:
		"""Get new preconfigured boto3 session for offsite backup provider."""
		return Session(
			aws_access_key_id=self.offsite_backups_access_key_id,
			aws_secret_access_key=self.get_password(
				"offsite_backups_secret_access_key", raise_exception=False
			),
			region_name="ap-south-1",
		)

	@property
	def boto3_iam_client(self):
		return boto3.client(
			"iam",
			aws_access_key_id=self.aws_access_key_id,
			aws_secret_access_key=self.get_password("aws_secret_access_key"),
		)

	@classmethod
	def is_offsite_setup(cls):
		return any(
			frappe.db.get_value(
				"Press Settings",
				"Press Settings",
				["aws_s3_bucket", "offsite_backups_access_key_id"],
			)
		)

	@property
	def telegram(self):
		return Telegram

	@property
	def telegram_message(self):
		return TelegramMessage

	@property
	def twilio_client(self) -> Client:
		account_sid = self.twilio_account_sid
		api_key_sid = self.twilio_api_key_sid
		api_key_secret = self.get_password("twilio_api_key_secret")
		return Client(api_key_sid, api_key_secret, account_sid)

	def get_default_apps(self):
		if hasattr(self, "enable_app_grouping") and hasattr(self, "default_apps"):  # noqa
			if self.enable_app_grouping:
				return [app.app for app in self.default_apps]
		return []
