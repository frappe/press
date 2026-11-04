# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

if TYPE_CHECKING:
	from press.saas.doctype.grove_trial_product.grove_trial_product import GroveTrialProduct

# Connect, read: a job must not hang on a Grove that is down.
TIMEOUT = (30, 90)
# What a Grove that is down or in maintenance answers.
UNAVAILABLE = (502, 503, 504)


class GroveSettings(Document):
	"""Where Grove is and the control credential Press calls it with. A pool of keys per Product
	Trial (`trial_products`) is minted ahead under `trial_team` there, each capped at `trial_key_cap`
	for its life and in the row's Model Group; a Product Trial site takes one of its product, and
	Press revokes it `trial_key_revoke_after_days` later."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.saas.doctype.grove_trial_product.grove_trial_product import GroveTrialProduct

		base_url: DF.Data | None
		control_api_key: DF.Data | None
		control_api_secret: DF.Password | None
		pause_key_assignment: DF.Check
		pause_pool_refill: DF.Check
		trial_key_cap: DF.Currency
		trial_key_geography: DF.Data | None
		trial_key_revoke_after_days: DF.Int
		trial_products: DF.Table[GroveTrialProduct]
		trial_team: DF.Data | None
	# end: auto-generated types

	@property
	def is_enrolled(self) -> bool:
		return bool(self.base_url and self.control_api_key)

	def validate(self):
		self.base_url = (self.base_url or "").strip().rstrip("/")
		products = [row.product_trial for row in self.trial_products]
		if len(products) != len(set(products)):
			frappe.throw(_("One pool row per product."))
		if any(cint(row.pool_size) for row in self.trial_products) and not self.trial_key_geography:
			frappe.throw(_("Set Trial Key Geography before sizing a pool."))

	def set_credential(self, credential: dict):
		self.control_api_key = credential["api_key"]
		self.control_api_secret = credential["api_secret"]
		self.save()

	def call(self, method: str, **body):
		"""POST `method` at Grove as Press; Grove's own refusal line is what the caller reads."""
		if not self.is_enrolled:
			frappe.throw(_("AI is not set up: enroll Press at Grove in Grove Settings."))
		headers = {"Authorization": f"token {self.control_api_key}:{self.get_password('control_api_secret')}"}
		try:
			response = requests.post(
				f"{self.base_url}/api/method/{method}", json=body, headers=headers, timeout=TIMEOUT
			)
		except (requests.ConnectionError, requests.Timeout) as e:
			raise frappe.ValidationError(_("Grove can't be reached right now.")) from e
		return read(response)

	def provision_key(self, row: GroveTrialProduct, title: str) -> dict:
		"""Mint one key into `row`'s product's pool under the trial team: titled `title` (the Grove Trial
		Key record's id, so Grove's list names Press's record), in the trial geography, at the trial cap,
		no expiry (Press revokes it on its own clock). What it may call is the team's, set at Grove, plus
		the row's Model Group when it names one. `{name, geography, gateway_url, api_key}`; the secret is
		in this answer and nowhere else at Grove."""
		body = {
			"team": self.trial_team,
			"title": title,
			"geography": self.trial_key_geography,
			"cap": self.trial_key_cap,
		}
		if row.model_group:
			body["model_groups"] = [row.model_group]
		return self.call("grove.api.keys.provision_key", **body)

	def update_caps(self, team: str, caps: dict[str, float]) -> list[dict]:
		"""Set several keys' caps at once, {key: USD}; Grove saves all or none."""
		return self.call("grove.api.keys.update_caps", team=team, caps=caps) or []

	def revoke_key(self, name: str, team: str):
		"""Under `team`, the one the key was minted under: Grove refuses any other."""
		return self.call("grove.api.keys.revoke_key", team=team, key=name)


def read(response: requests.Response):
	if response.status_code in UNAVAILABLE:
		frappe.throw(_("Grove is unavailable ({0}).").format(response.status_code))
	if response.status_code >= 400:
		detail = refusal_message(response) or f"{response.status_code}: {response.text[:500]}"
		frappe.throw(_("Grove refused: {0}").format(detail))
	return response.json().get("message", {})


def refusal_message(response: requests.Response) -> str | None:
	"""Grove's own sentence from a refusal: the first of Frappe's `_server_messages`, else its
	`exception` line. None when the body is not Frappe's."""
	try:
		body = response.json()
		messages = [
			json.loads(raw).get("message") for raw in json.loads(body.get("_server_messages") or "[]")
		]
	except (ValueError, TypeError, AttributeError):
		return None
	return next((message for message in messages if message), None) or body.get("exception")


# Plain whitelisted calls, not doc methods: a form's doc method gets its arguments nested under
# `args`, where a secret cannot be popped from the request before it is logged.


@frappe.whitelist(methods=["POST"])
def enroll():
	"""Desk button: exchange the bootstrap secret Grove was given for Press's own control
	credential. The secret is popped from the raw request, so it is never logged."""
	frappe.only_for("System Manager")
	secret = frappe.local.form_dict.pop("bootstrap_secret", None)
	if not secret:
		frappe.throw(_("Bootstrap secret is required."))
	settings: GroveSettings = frappe.get_single("Grove Settings")
	if not settings.base_url:
		frappe.throw(_("Set the Grove URL first."))

	body = {"email": f"press@{frappe.local.site}", "token": secret}
	response = requests.post(
		f"{settings.base_url}/api/method/grove.api.control.create_control_client", json=body, timeout=TIMEOUT
	)
	settings.set_credential(read(response))


@frappe.whitelist(methods=["POST"])
def rotate_credential():
	"""Desk button: a new control secret from Grove. The old one stops at once."""
	frappe.only_for("System Manager")
	settings: GroveSettings = frappe.get_single("Grove Settings")
	settings.set_credential(settings.call("grove.api.control.create_control_client_key"))
