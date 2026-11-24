# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from press.utils.plan_change import attach_plan_details, snapshot_plans
from press.utils.webhook import create_webhook_event

# What the dashboard reads to describe a site plan: its price and its limits.
SITE_PLAN_FIELDS = (
	"plan_title",
	"price_inr",
	"price_usd",
	"cpu_time_per_day",
	"max_storage_usage",
	"dedicated_server_plan",
)


class SitePlanChange(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from_plan: DF.Link | None
		from_plan_snapshot: DF.JSON | None
		site: DF.Link
		team: DF.Link | None
		timestamp: DF.Datetime | None
		to_plan: DF.Link
		to_plan_snapshot: DF.JSON | None
		type: DF.Literal["", "Initial Plan", "Upgrade", "Downgrade"]
	# end: auto-generated types

	dashboard_fields = ("from_plan", "to_plan", "type", "site", "timestamp")

	@staticmethod
	def get_list_query(query, **list_args):
		rows = query.run(as_dict=True)
		attach_plan_details(rows, "Site Plan Change", "Site Plan", SITE_PLAN_FIELDS)
		return rows

	def validate(self):
		if not self.from_plan and self.to_plan:
			self.type = "Initial Plan"

		if self.from_plan and self.to_plan and self.from_plan == self.to_plan:
			frappe.throw(
				"The new plan is the same as the current plan. Please choose a different plan to change to."
			)

		if self.from_plan and not self.type:
			from_plan_value = frappe.db.get_value("Site Plan", self.from_plan, "price_usd")
			to_plan_value = frappe.db.get_value("Site Plan", self.to_plan, "price_usd")
			self.type = "Downgrade" if from_plan_value > to_plan_value else "Upgrade"

		if (
			self.from_plan
			and self.to_plan
			and self.type == "Downgrade"
			and not frappe.db.get_value("Site Plan", self.to_plan, "allow_downgrading_from_other_plan")
		):
			frappe.throw(
				f"Sorry, you cannot downgrade to {self.to_plan} from {self.from_plan}. <a href='https://docs.frappe.io/cloud/tiny-plan#why-cant-i-upgrade-to-this-plan-'><u>Why?</u></a>"
			)

		if self.type == "Initial Plan":
			self.from_plan = ""

		if self.is_new():
			snapshot_plans(self, "Site Plan", SITE_PLAN_FIELDS)

	def after_insert(self):
		if self.team != "Administrator":
			create_webhook_event("Site Plan Change", self, self.team)

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
