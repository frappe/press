# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class IncidentSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.incident_settings_self_hosted_user.incident_settings_self_hosted_user import (
			IncidentSettingsSelfHostedUser,
		)
		from press.press.doctype.incident_settings_user.incident_settings_user import (
			IncidentSettingsUser,
		)

		call_repeat_interval_day: DF.Duration | None
		call_repeat_interval_night: DF.Duration | None
		call_threshold_day: DF.Duration | None
		call_threshold_night: DF.Duration | None
		confirmation_threshold_day: DF.Duration | None
		confirmation_threshold_night: DF.Duration | None
		email_alerts: DF.Check
		enable_incident_detection: DF.Check
		phone_call_alerts: DF.Check
		self_hosted_users: DF.Table[IncidentSettingsSelfHostedUser]
		users: DF.Table[IncidentSettingsUser]
	# end: auto-generated types

	pass
