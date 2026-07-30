# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.utils.raven import send_raven_message

RAVEN_INCIDENTS_CHANNEL = "frappe-cloud-incidents"


class IncidentSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.incident_settings_night_shift.incident_settings_night_shift import (
			IncidentSettingsNightShift,
		)
		from press.press.doctype.incident_settings_self_hosted_user.incident_settings_self_hosted_user import (
			IncidentSettingsSelfHostedUser,
		)
		from press.press.doctype.incident_settings_user.incident_settings_user import IncidentSettingsUser

		call_repeat_interval_day: DF.Duration | None
		call_repeat_interval_night: DF.Duration | None
		call_threshold_day: DF.Duration | None
		call_threshold_night: DF.Duration | None
		confirmation_threshold_day: DF.Duration | None
		confirmation_threshold_night: DF.Duration | None
		email_alerts: DF.Check
		enable_incident_detection: DF.Check
		grafana_screenshots: DF.Check
		night_shift_call_limit: DF.Int
		night_shifts: DF.Table[IncidentSettingsNightShift]
		phone_call_alerts: DF.Check
		self_hosted_users: DF.Table[IncidentSettingsSelfHostedUser]
		users: DF.Table[IncidentSettingsUser]
		wait_time_post_investigator_actions: DF.Duration | None
	# end: auto-generated types

	pass


def alert_if_phone_call_alerts_disabled():
	"""Nobody gets paged when phone call alerts are off. Nag hourly until it's turned back on."""
	if frappe.db.get_single_value("Incident Settings", "phone_call_alerts"):
		return

	send_raven_message(
		"⚠️ **Phone call alerts are disabled** in "
		f"[Incident Settings]({frappe.utils.get_url('/app/incident-settings')}). "
		"Incidents won't call anyone.",
		RAVEN_INCIDENTS_CHANNEL,
	)
