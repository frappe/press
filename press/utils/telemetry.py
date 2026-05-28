from __future__ import annotations

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


pulse_site = frappe.db.get_single_value("Press Settings", "pulse_site")
pulse_api_key = frappe.db.get_single_value("Press Settings", "pulse_api_key")


def capture_pulse(event, data):
	if not pulse_site or not pulse_api_key:
		return

	try:
		requests.post(
			f"https://{pulse_site}/api/method/pulse.api.bulk_ingest",
			headers={
				"Content-Type": "application/json",
				"X-Pulse-API-Key": pulse_api_key,
			},
			data=frappe.as_json(
				{
					"events": [
						{
							"event": event,
							"captured_at": frappe.utils.now(),
							"app": "press",
							"user": None,  # can be session user if needed
							"site": frappe.local.site,
							"properties": data,
						}
					]
				}
			),
			timeout=10,
		)
	except Exception as e:
		log_error("Failed to capture event to pulse", e)
