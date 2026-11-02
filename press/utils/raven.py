# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
import requests

from press.utils import log_error

RAVEN_BOT_ID = "Frappe Notifications"


def send_raven_message(text: str, channel: str) -> None:
	settings = frappe.get_single("Press Settings")
	url = settings.raven_url
	api_key = settings.raven_access_key_id
	api_secret = settings.get_password("raven_secret_access_key", raise_exception=False)
	if not url or not api_key or not api_secret:
		log_error("Raven settings missing", channel=channel)
		return

	headers = {
		"Authorization": f"token {api_key}:{api_secret}",
		"Content-Type": "application/json",
	}

	try:
		response = requests.post(
			url,
			json={"bot_id": RAVEN_BOT_ID, "message": text, "channel_id": channel},
			headers=headers,
			timeout=30,
		)
	except requests.exceptions.RequestException as exc:
		log_error("Failed to send message to Raven", exception=exc, channel=channel)
		return

	if response.ok:
		return

	log_error(
		"Failed to send message to Raven",
		channel=channel,
		status_code=response.status_code,
		response=response.text[:1000],
	)
