# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.press.ui_action.base_action import BaseAction


class ToggleSiteActivate(BaseAction):
	def execute(self, site, activate):
		site = frappe.get_doc("Site", site)
		if activate is True and site.status != "Active":
			site.activate()
		elif activate is False and site.status == "Active":
			site.deactivate()
