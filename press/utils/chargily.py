# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import hashlib
import hmac

import frappe
import requests


def get_chargily_client():
	"""Get configured Chargily API client settings."""
	settings = frappe.get_cached_doc("Press Settings")
	api_secret = settings.get_password("chargily_api_secret")
	test_mode = settings.chargily_test_mode

	if not api_secret:
		frappe.throw("Chargily API Secret not configured in Press Settings")

	base_url = (
		"https://pay.chargily.net/test/api/v2/"
		if test_mode
		else "https://pay.chargily.net/api/v2/"
	)

	return {
		"base_url": base_url,
		"headers": {
			"Authorization": f"Bearer {api_secret}",
			"Content-Type": "application/json",
		},
	}


def create_checkout(
	amount,
	description,
	invoice_name=None,
	team_name=None,
	success_url=None,
	failure_url=None,
	payment_method=None,
):
	"""Create a Chargily Pay checkout session."""
	client = get_chargily_client()
	press_url = frappe.utils.get_url()

	if not success_url:
		success_url = f"{press_url}/dashboard/billing?payment=success"
	if not failure_url:
		failure_url = f"{press_url}/dashboard/billing?payment=failed"

	webhook_url = (
		f"{press_url}/api/method/press.press.doctype"
		".chargily_webhook_log.chargily_webhook_log.chargily_webhook_handler"
	)

	metadata = []
	if invoice_name:
		metadata.append({"key": "invoice", "value": invoice_name})
	if team_name:
		metadata.append({"key": "team", "value": team_name})

	data = {
		"amount": int(amount),
		"currency": "dzd",
		"success_url": success_url,
		"failure_url": failure_url,
		"webhook_endpoint": webhook_url,
		"description": description or "Paiement Cloud",
		"locale": "fr",
		"metadata": metadata,
	}

	if payment_method and payment_method in ("edahabia", "cib"):
		data["payment_method"] = payment_method

	response = requests.post(
		f"{client['base_url']}checkouts",
		headers=client["headers"],
		json=data,
		timeout=30,
	)
	response.raise_for_status()
	return response.json()


def get_checkout(checkout_id):
	"""Retrieve a checkout by ID."""
	client = get_chargily_client()
	response = requests.get(
		f"{client['base_url']}checkouts/{checkout_id}",
		headers=client["headers"],
		timeout=30,
	)
	response.raise_for_status()
	return response.json()


def validate_signature(secret, signature, payload):
	"""Validate Chargily webhook HMAC-SHA256 signature."""
	expected = hmac.new(
		secret.encode("utf-8"),
		payload.encode("utf-8"),
		hashlib.sha256,
	).hexdigest()
	return hmac.compare_digest(expected, signature)
