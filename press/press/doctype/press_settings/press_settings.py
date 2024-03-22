# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import boto3
import frappe
from boto3.session import Session
from twilio.rest import Client
from frappe.model.document import Document
from frappe.utils import get_url

from press.api.billing import get_stripe
from press.telegram_utils import Telegram


class PressSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.erpnext_app.erpnext_app import ERPNextApp

		agent_github_access_token: DF.Data | None
		agent_repository_owner: DF.Data | None
		allow_developer_account: DF.Check
		app_include_script: DF.Data | None
		auto_update_queue_size: DF.Int
		aws_access_key_id: DF.Data | None
		aws_s3_bucket: DF.Data | None
		aws_secret_access_key: DF.Password | None
		backup_interval: DF.Int
		backup_limit: DF.Int
		backup_offset: DF.Int
		backup_region: DF.Data | None
		backup_rotation_scheme: DF.Literal["FIFO", "Grandfather-father-son"]
		bench_configuration: DF.Code
		build_directory: DF.Data | None
		central_migration_server: DF.Link | None
		certbot_directory: DF.Data
		clone_directory: DF.Data | None
		cluster: DF.Link | None
		code_server: DF.Data | None
		code_server_password: DF.Data | None
		commission: DF.Float
		compress_app_cache: DF.Check
		data_40: DF.Data | None
		default_outgoing_id: DF.Data | None
		default_outgoing_pass: DF.Data | None
		docker_registry_namespace: DF.Data | None
		docker_registry_password: DF.Data | None
		docker_registry_url: DF.Data | None
		docker_registry_username: DF.Data | None
		docker_remote_builder_server: DF.Link | None
		docker_remote_builder_ssh: DF.Data | None
		domain: DF.Link | None
		eff_registration_email: DF.Data
		enable_google_oauth: DF.Check
		enable_site_pooling: DF.Check
		enforce_storage_limits: DF.Check
		erpnext_api_key: DF.Data | None
		erpnext_api_secret: DF.Password | None
		erpnext_apps: DF.Table[ERPNextApp]
		erpnext_cluster: DF.Link | None
		erpnext_domain: DF.Link | None
		erpnext_group: DF.Link | None
		erpnext_plan: DF.Link | None
		erpnext_url: DF.Data | None
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
		github_webhook_secret: DF.Data | None
		gst_percentage: DF.Float
		hybrid_cluster: DF.Link | None
		hybrid_domain: DF.Link | None
		log_server: DF.Link | None
		mailgun_api_key: DF.Data | None
		max_allowed_screenshots: DF.Int
		monitor_server: DF.Link | None
		monitor_token: DF.Data | None
		ngrok_auth_token: DF.Data | None
		offsite_backups_access_key_id: DF.Data | None
		offsite_backups_count: DF.Int
		offsite_backups_provider: DF.Literal["AWS S3"]
		offsite_backups_secret_access_key: DF.Password | None
		plausible_api_key: DF.Password | None
		plausible_site_id: DF.Data | None
		plausible_url: DF.Data | None
		press_monitoring_password: DF.Password | None
		print_format: DF.Data | None
		publish_docs: DF.Check
		razorpay_key_id: DF.Data | None
		razorpay_key_secret: DF.Password | None
		razorpay_webhook_secret: DF.Data | None
		realtime_job_updates: DF.Check
		remote_access_key_id: DF.Data | None
		remote_link_expiry: DF.Int
		remote_secret_access_key: DF.Password | None
		remote_uploads_bucket: DF.Data | None
		root_domain: DF.Data | None
		rsa_key_size: DF.Literal["2048", "3072", "4096"]
		spaces_domain: DF.Link | None
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
		trial_sites_count: DF.Int
		twilio_account_sid: DF.Data | None
		twilio_api_key_secret: DF.Password | None
		twilio_api_key_sid: DF.Data | None
		twilio_phone_number: DF.Phone | None
		usd_rate: DF.Float
		use_app_cache: DF.Check
		use_delta_builds: DF.Check
		use_staging_ca: DF.Check
		verify_cards_with_micro_charge: DF.Literal[
			"No", "Only INR", "Only USD", "Both INR and USD"
		]
		webroot_directory: DF.Data | None
	# end: auto-generated types

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
		manifest = {
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
		return manifest

	@property
	def boto3_offsite_backup_session(self) -> Session:
		"""Get new preconfigured boto3 session for offisite backup provider."""
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
	def twilio_client(self) -> Client:
		account_sid = self.twilio_account_sid
		api_key_sid = self.twilio_api_key_sid
		api_key_secret = self.get_password("twilio_api_key_secret")
		return Client(api_key_sid, api_key_secret, account_sid)
