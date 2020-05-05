# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


class SitePlanChange(Document):
	def validate(self):
		if self.from_plan and not self.type:
			from_plan_value = frappe.db.get_value("Plan", self.from_plan, "price_usd")
			to_plan_value = frappe.db.get_value("Plan", self.to_plan, "price_usd")
			self.type = "Downgrade" if from_plan_value > to_plan_value else "Upgrade"

		if self.type == "Initial Plan":
			self.from_plan = ""

	def after_insert(self):
		if self.type == "Initial Plan":
			return

		site = frappe.get_doc("Site", self.site)

		if self.from_plan and self.from_plan != site.plan:
			frappe.throw(
				_("Site {0} is currently on {1} plan and not {2}").format(
					site.name, site.plan, self.from_plan
				)
			)
		site.plan = self.to_plan
		site.flags.updater_reference = {
			"doctype": self.doctype,
			"docname": self.name,
			"label": _("via Site Plan Change"),
		}
		site.save()
