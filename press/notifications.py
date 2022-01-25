# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe


def get_notification_config():
	return {
		"for_doctype": {
			"Site": {"status": "Active"},
			"Bench": {"status": "Active"},
			"Server": {"status": "Active"},
			"Database Server": {"status": "Active"},
			"Proxy Server": {"status": "Active"},
		},
	}
