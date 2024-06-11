# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


from frappe import _


def get_data():
	return {
		"fieldname": "server",
		"transactions": [
			{"label": _("Logs"), "items": ["Agent Job", "Ansible Play"]},
		],
	}
