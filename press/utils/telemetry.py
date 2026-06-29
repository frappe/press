from __future__ import annotations

import hashlib
import re
from contextlib import suppress

import frappe
import requests
from posthog import Posthog

from press.utils import log_error


def init_telemetry():
	"""Init posthog for server side telemetry."""
	if hasattr(frappe.local, "posthog"):
		return

	posthog_host = frappe.conf.get("posthog_host")
	posthog_project_id = frappe.conf.get("posthog_project_id")

	if not posthog_host or not posthog_project_id:
		return

	with suppress(Exception):
		frappe.local.posthog = Posthog(posthog_project_id, host=posthog_host)


def capture(event, app, distinct_id=None):
	init_telemetry()
	ph: Posthog = getattr(frappe.local, "posthog", None)
	with suppress(Exception):
		properties = {}
		if app == "fc_product_trial":
			properties = {"product_trial": True}
		ph and ph.capture(
			distinct_id=distinct_id or frappe.local.site, event=f"{app}_{event}", properties=properties
		)


def identify(site, **kwargs):
	init_telemetry()
	ph: Posthog = getattr(frappe.local, "posthog", None)
	with suppress(Exception):
		ph and ph.identify(site, kwargs)


@frappe.whitelist(allow_guest=True)
def capture_read_event(email: str | None = None):
	try:
		capture("read_email", "fc_signup", email)
	except Exception as e:
		log_error("Failed to capture read_email event", e)
	finally:
		frappe.response.update(frappe.utils.get_imaginary_pixel_response())


def _pulse_post(method: str, payload: dict):
	"""POST to a Pulse API method server-to-server (key in the X-Pulse-API-Key header).

	Telemetry never raises to the caller: a dropped event or a missed identity stitch
	must not break the signup/billing flow it rides on, and identify self-heals on the
	next change. We post directly (no framework client) because cloud.frappe.io's
	framework predates `frappe.utils.telemetry.pulse`.
	"""
	pulse_site = frappe.db.get_single_value("Press Settings", "pulse_site")
	pulse_api_key = frappe.db.get_single_value("Press Settings", "pulse_api_key")

	if not pulse_site or not pulse_api_key:
		return

	try:
		requests.post(
			f"https://{pulse_site}/api/method/pulse.api.{method}",
			headers={
				"Content-Type": "application/json",
				"X-Pulse-API-Key": pulse_api_key,
			},
			data=frappe.as_json(payload),
			timeout=10,
		)
	except Exception:
		log_error(f"Failed to call pulse.api.{method}")


def capture_pulse(event, data):
	_pulse_post(
		"bulk_ingest",
		{
			"events": [
				{
					"event_name": event,
					"captured_at": frappe.utils.now(),
					"app": "press",
					"user": anonymize_user(frappe.session.user),
					"site": frappe.local.site,
					"properties": data,
				}
			]
		},
	)


def pulse_identify(user: str, properties: dict | None = None):
	"""Attach attributes to a person (upsert their Pulse Person profile)."""
	if not user:
		return
	_pulse_post(
		"identify",
		{
			"user": anonymize_user(user),
			"properties": properties or {},
		},
	)


def pulse_alias(previous_id: str, user: str):
	"""Link a pre-signup anonymous browser id to the known account user."""
	if not previous_id or not user:
		return
	_pulse_post(
		"alias",
		{
			"previous_id": previous_id,
			"user": anonymize_user(user),
		},
	)


def anonymize_user(user: str | None) -> str | None:
	"""Per-site-salted anonymized `user_…` id, matching frappe's telemetry client.

	Replicated here (not imported) because cloud.frappe.io's framework predates the
	pulse client. Same email + site always yields the same id, so press can mint the
	account's `user_…` deterministically as the `alias`/`identify` target.
	"""
	if not user or user in frappe.STANDARD_USERS:
		return user

	# Already anonymized — leave as-is.
	if re.match(r"^user_[a-f0-9]{12}$", user):
		return user

	site_salt = frappe.local.site or "default"
	user_hash = hashlib.sha256(f"{user}:{site_salt}".encode()).hexdigest()
	return f"user_{user_hash[:12]}"
