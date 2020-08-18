# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
from frappe import _


def get_data():
	return {
		"fieldname": "site",
		"transactions": [
			{
				"label": _("Usage"),
				"items": ["Site Usage", "Remote File"]
			},
			{"label": _("Billing"), "items": ["Payment Ledger Entry"]},
			{
				"label": _("Related Documents"),
				"items": ["Site Domain", "Site Activity", "Site Plan Change"],
			},
			{
				"label": _("Logs"),
				"items": [
					"Agent Job",
					"Site Backup",
					"Site Update",
					"Site Uptime Log",
					"Site Job Log",
					"Site Request Log",
				],
			},
		],
	}
