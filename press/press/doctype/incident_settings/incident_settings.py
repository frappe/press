# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils.data import cint

DAY_HOURS = range(9, 18)


class IncidentSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.incident_settings_self_hosted_user.incident_settings_self_hosted_user import (
			IncidentSettingsSelfHostedUser,
		)
		from press.press.doctype.incident_settings_user.incident_settings_user import IncidentSettingsUser

		call_threshold_day: DF.Duration
		call_threshold_night: DF.Duration
		confirmation_threshold_day: DF.Duration
		confirmation_threshold_night: DF.Duration
		email_alerts: DF.Check
		enable_incident_detection: DF.Check
		grafana_screenshots: DF.Check
		minimum_firing_instances: DF.Int
		minimum_firing_instances_in_percent: DF.Percent
		phone_call_alerts: DF.Check
		self_hosted_users: DF.Table[IncidentSettingsSelfHostedUser]
		users: DF.Table[IncidentSettingsUser]
		wait_time_post_investigator_actions: DF.Duration | None
	# end: auto-generated types

	@property
	def confirmation_threshold_seconds(self) -> int:
		"""
		After this specific time, the system can move an incident to "Confirmed" status
		if it is still in "Validating" state
		"""
		if frappe.utils.now_datetime().hour in range(9, 18):  # 9am to 6pm
			return cint(self.confirmation_threshold_day)

		return cint(self.confirmation_threshold_night)

	@property
	def call_threshold_seconds(self) -> int:
		"""
		After this specific time, the system can call the on-call engineers
		if the incident is still in "Confirmed" state
		"""
		if frappe.utils.now_datetime().hour in DAY_HOURS:
			return cint(self.call_threshold_day)

		return cint(self.call_threshold_night)

	@property
	def call_repeat_interval_seconds(self) -> int:
		"""
		If someone has acknowledged the incident but it hasn't resolved yet
		then after this specific time, the system can call the on-call engineers again
		"""
		return 15 * 60  # 15 minutes
