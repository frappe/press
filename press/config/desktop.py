# -*- coding: utf-8 -*-

from frappe import _


def get_data():
	return [
		{
			"module_name": "Press",
			"category": "Modules",
			"color": "grey",
			"description": "Managed Frappe Hosting",
			"icon": "octicon octicon-rocket",
			"type": "module",
			"label": _("Press"),
			"reverse": 1,
		}
	]
