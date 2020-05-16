# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def get_data():
	return {
		"fieldname": "team",
		"transactions": [
			{"label": _("Related Documents"), "items": ["Site"]},
			{"label": _("Billing"), "items": ["Payment", "Payment Ledger Entry"]},
		],
	}
