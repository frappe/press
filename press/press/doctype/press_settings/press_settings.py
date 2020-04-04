# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.utils import log_error
from press.api.billing import get_stripe


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
				"payment_method.attached",
				"invoice.payment_action_required",
				"invoice.payment_succeeded",
				"invoice.payment_failed",
				"customer.subscription.updated",
			],
		)
		self.stripe_webhook_endpoint_id = webhook["id"]
		self.stripe_webhook_secret = webhook["secret"]
		self.flags.ignore_mandatory = True
		self.save()
