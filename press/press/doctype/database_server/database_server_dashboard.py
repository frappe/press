# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


from frappe import _


def get_data():
	return {
		"fieldname": "server",
		"non_standard_fieldnames": {"Server": "database_server"},
		"transactions": [
			{"label": _("Related Documents"), "items": ["Server"]},
			{"label": _("Logs"), "items": ["Agent Job", "Ansible Play"]},
			{"label": _("Report"), "items": ["Performance Report"]},
		],
	}
