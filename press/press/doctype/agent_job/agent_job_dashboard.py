# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from frappe import _


def get_data():
	return {
		"fieldname": "agent_job",
		"transactions": [
			{
				"label": _("Related Documents"),
				"items": ["Agent Job Step"],
			},
		],
	}
