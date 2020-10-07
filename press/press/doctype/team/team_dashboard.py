# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
from frappe import _


def get_data():
	return {
		"fieldname": "team",
		"transactions": [
			{"label": _("Related Documents"), "items": ["Site", "Frappe App", "Release Group"]},
			{"label": _("Billing"), "items": ["Invoice", "Payment Ledger Entry"]},
		],
	}
