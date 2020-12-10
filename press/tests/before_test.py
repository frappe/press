# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import os


def execute():
	settings = frappe.get_single("Press Settings")
	if not settings.stripe_account:
		stripe_account = create_test_stripe_account()
		if stripe_account:
			settings.stripe_account = stripe_account.name
			settings.save()


def create_test_stripe_account():
	publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY")
	secret_key = os.environ.get("STRIPE_SECRET_KEY")
	if publishable_key and secret_key:
		return frappe.get_doc(
			doctype="Stripe Settings",
			gateway_name="Test",
			publishable_key=publishable_key,
			secret_key=secret_key,
		).insert()
