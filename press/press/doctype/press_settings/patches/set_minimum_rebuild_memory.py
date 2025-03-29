# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import typing

import frappe

if typing.TYPE_CHECKING:
	from press.press.doctype.press_settings.press_settings import PressSettings


def execute():
	frappe.reload_doctype("Press Settings")
	settings: PressSettings = frappe.get_single("Press Settings")

	if not settings.minimum_rebuild_memory:
		settings.minimum_rebuild_memory = 2
		settings.save()
