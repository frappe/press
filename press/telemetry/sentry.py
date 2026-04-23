import contextlib
import os

import frappe
from sentry_sdk.hub import Hub

from press.telemetry.monitor import get_user_details


def set_context(key: str, value: dict):
	if not frappe.get_system_settings("enable_telemetry"):
		return
	with contextlib.suppress(Exception):
		hub: Hub = Hub.current
		with hub.configure_scope() as scope:
			if not (
				(
					os.getenv("ENABLE_SENTRY_DB_MONITORING") is None
					or os.getenv("SENTRY_TRACING_SAMPLE_RATE") is None
					or os.getenv("SENTRY_PROFILING_SAMPLE_RATE") is None
				)
				and frappe.request
			):
				scope.set_context(key, value)


def add_user_context():
	set_context("user_details", get_user_details())
