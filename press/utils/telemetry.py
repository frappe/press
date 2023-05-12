from contextlib import suppress
from posthog import Posthog
import frappe


def init_telemetry():
	"""Init posthog for server side telemetry."""
	if hasattr(frappe.local, "posthog"):
		return

	if not frappe.get_system_settings("enable_telemetry"):
		return

	posthog_host = frappe.conf.get("posthog_host")
	posthog_project_id = frappe.conf.get("posthog_project_id")

	if not posthog_host or not posthog_project_id:
		return

	with suppress(Exception):
		frappe.local.posthog = Posthog(posthog_project_id, host=posthog_host)


def capture(event, app, site=None):
	init_telemetry()
	ph: Posthog = getattr(frappe.local, "posthog", None)
	with suppress(Exception):
		ph and ph.capture(site or frappe.local.site, f"{app}_{event}")
