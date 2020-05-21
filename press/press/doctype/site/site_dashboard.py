# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from frappe import _


def get_data():
	return {
		"fieldname": "site",
		"transactions": [
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
			{"label": _("Billing"), "items": ["Payment Ledger Entry"]},
		],
	}
