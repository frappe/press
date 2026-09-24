# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt


from frappe import _


def get_data():
	return {
		"fieldname": "reference_name",
		"dynamic_links": {"reference_name": ["Virtual Disk Resize", "reference_doctype"]},
		"transactions": [{"label": _("Logs"), "items": ["Error Log"]}],
	}
