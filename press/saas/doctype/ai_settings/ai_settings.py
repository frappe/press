# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
import requests
from frappe import _
from frappe.model.document import Document

# Grove holds one team for every Press trial site, on a tier of its own: unlimited keys, a large
# spend limit and trial rate limits, tuned there. Press names both at enroll; Grove owns the values.
PRESS_TEAM = "Press Team"
PRESS_TIER = "Press Trial"
# Connect, read: a job must not hang on a Grove that is down.
TIMEOUT = (30, 90)
# What a Grove that is down or in maintenance answers.
UNAVAILABLE = (502, 503, 504)


class AISettings(Document):
	"""Where Grove is and the control credential Press calls it with. Every Product Trial site gets
	one Grove key under Press's team there, capped at `trial_key_cap` for the life of the key."""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_url: DF.Data | None
		control_api_key: DF.Data | None
		control_api_secret: DF.Password | None
		trial_key_cap: DF.Currency
	# end: auto-generated types

	@property
	def is_enrolled(self) -> bool:
		return bool(self.base_url and self.control_api_key)

	def validate(self):
		self.base_url = (self.base_url or "").strip().rstrip("/")

	def set_credential(self, credential: dict):
		self.control_api_key = credential["api_key"]
		self.control_api_secret = credential["api_secret"]
		self.save()

	def call(self, method: str, **body):
		"""POST `method` at Grove as Press; Grove's own refusal line is what the caller reads."""
		if not self.is_enrolled:
			frappe.throw(_("AI is not set up: enroll Press at Grove in AI Settings."))
		headers = {"Authorization": f"token {self.control_api_key}:{self.get_password('control_api_secret')}"}
		try:
			response = requests.post(
				f"{self.base_url}/api/method/{method}", json=body, headers=headers, timeout=TIMEOUT
			)
		except (requests.ConnectionError, requests.Timeout) as e:
			raise frappe.ValidationError(_("Grove can't be reached right now.")) from e
		return read(response)

	def provision_key(self, site: str) -> dict:
		"""Mint `site`'s key under Press's team at the trial cap, titled by the site:
		`{name, geography, gateway_url, api_key}`; the secret is in this answer and nowhere else."""
		return self.call("grove.api.keys.provision_key", team=PRESS_TEAM, title=site, cap=self.trial_key_cap)

	def revoke_key(self, name: str):
		return self.call("grove.api.keys.revoke_key", team=PRESS_TEAM, key=name)


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
	credential, then register Press's team on its tier. The secret is popped from the raw request,
	so it is never logged."""
	frappe.only_for("System Manager")
	secret = frappe.local.form_dict.pop("bootstrap_secret", None)
	if not secret:
		frappe.throw(_("Bootstrap secret is required."))
	settings: AISettings = frappe.get_single("AI Settings")
	if not settings.base_url:
		frappe.throw(_("Set the Grove URL first."))

	body = {"email": f"press@{frappe.local.site}", "token": secret}
	response = requests.post(
		f"{settings.base_url}/api/method/grove.api.control.create_control_client", json=body, timeout=TIMEOUT
	)
	settings.set_credential(read(response))
	settings.call("grove.api.teams.provision_team", team=PRESS_TEAM)
	settings.call("grove.api.teams.update_team", team=PRESS_TEAM, tier=PRESS_TIER)


@frappe.whitelist(methods=["POST"])
def rotate_credential():
	"""Desk button: a new control secret from Grove. The old one stops at once."""
	frappe.only_for("System Manager")
	settings: AISettings = frappe.get_single("AI Settings")
	settings.set_credential(settings.call("grove.api.control.create_control_client_key"))
