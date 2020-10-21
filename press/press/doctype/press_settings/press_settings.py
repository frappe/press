# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.utils import log_error
from press.api.billing import get_stripe
from frappe.utils import get_url


class PressSettings(Document):
	def obtain_root_domain_tls_certificate(self):
		frappe.enqueue_doc(self.doctype, self.name, "_obtain_root_domain_tls_certificate")

	def _obtain_root_domain_tls_certificate(self):
		try:
			certificate = frappe.get_doc(
				{
					"doctype": "TLS Certificate",
					"wildcard": True,
					"domain": self.domain,
					"rsa_key_size": self.rsa_key_size,
				}
			).insert()
			self.wildcard_tls_certificate = certificate.name
			self.save()
		except Exception:
			log_error("Root Domain TLS Exception")

	def create_stripe_plans(self):
		stripe = get_stripe()
		product_name = "Frappe Cloud"
		product = stripe.Product.create(name=product_name, type="service")
		self.stripe_product_id = product.id

		usd_plan = stripe.Plan.create(
			usage_type="metered",
			aggregate_usage="sum",
			currency="usd",
			interval="month",
			product=product.id,
			nickname="USD Monthly",
			amount_decimal="1",
		)
		inr_plan = stripe.Plan.create(
			usage_type="metered",
			aggregate_usage="sum",
			currency="inr",
			interval="month",
			product=product.id,
			nickname="INR Monthly",
			amount_decimal="1",
		)

		self.stripe_inr_plan_id = inr_plan.id
		self.stripe_usd_plan_id = usd_plan.id
		self.flags.ignore_mandatory = True
		self.save()

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
