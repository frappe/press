# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


from frappe import _


def get_data():
	return {
		"fieldname": "play",
		"transactions": [{"label": _("Related Documents"), "items": ["Ansible Task"]}],
	}
