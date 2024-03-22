# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SitePlanChange(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from_plan: DF.Link | None
		site: DF.Link
		team: DF.Link | None
		timestamp: DF.Datetime | None
		to_plan: DF.Link
		type: DF.Literal["", "Initial Plan", "Upgrade", "Downgrade"]
	# end: auto-generated types

	def validate(self):
		if not self.from_plan and self.to_plan:
			self.type = "Initial Plan"

		if self.from_plan and not self.type:
			from_plan_value = frappe.db.get_value("Site Plan", self.from_plan, "price_usd")
			to_plan_value = frappe.db.get_value("Site Plan", self.to_plan, "price_usd")
			self.type = "Downgrade" if from_plan_value > to_plan_value else "Upgrade"

		if self.type == "Initial Plan":
			self.from_plan = ""

	def after_insert(self):
		if self.type == "Initial Plan":
			self.create_subscription()
			return

		# move this code to Server Scripts
		# if self.type == "Downgrade":
		# 	last_plan_change = frappe.get_last_doc(
		# 		"Site Plan Change", filters={"site": self.site, "team": self.team}
		# 	)
		# 	# check if last site plan change was made before 48 hours
		# 	if last_plan_change.creation > frappe.utils.add_days(None, -2):
		# 		frappe.throw("Cannot downgrade plan within 48 hours")

		self.change_subscription_plan()

	def create_subscription(self):
		frappe.get_doc(
			doctype="Subscription",
			team=self.team,
			document_type="Site",
			document_name=self.site,
			plan_type="Site Plan",
			plan=self.to_plan,
		).insert()

	def change_subscription_plan(self):
		site = frappe.get_doc("Site", self.site)
		subscription = site.subscription
		if not subscription:
			frappe.throw(f"No subscription for site {site.name}")

		if self.from_plan and self.from_plan != subscription.plan:
			frappe.throw(
				_("Site {0} is currently on {1} plan and not {2}").format(
					site.name, subscription.plan, self.from_plan
				)
			)

		subscription.plan = self.to_plan
		subscription.flags.updater_reference = {
			"doctype": self.doctype,
			"docname": self.name,
			"label": _("via Site Plan Change"),
		}
		subscription.enabled = 1
		subscription.save()
