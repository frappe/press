# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals


def get_data():
	return {
		"fieldname": "app",
		"non_standard_fieldnames": {
			"Application Source": "application",
			"Release Group": "application",
		},
		"transactions": [
			{"items": ["Bench", "Site"]},
			{"items": ["Application Source", "Release Group", "App Release"]},
		],
	}
