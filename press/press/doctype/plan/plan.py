# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from typing import List, Any

import frappe
from frappe.model.document import Document
from frappe.utils import rounded
from press.utils import get_current_team
from frappe.utils.data import cast


class Plan(Document):
	@property
	def period(self):
		return frappe.utils.get_last_day(None).day

	def get_price_per_day(self, currency):
		price = self.price_inr if currency == "INR" else self.price_usd
		price_per_day = rounded(price / self.period, 2)
		return price_per_day

	def get_price_for_interval(self, interval, currency):
		price_per_day = self.get_price_per_day(currency)

		if interval == "Daily":
			return price_per_day

		if interval == "Monthly":
			return rounded(price_per_day * 30)


def get_plan_config(name):
	cpu_time = frappe.db.get_value("Plan", name, "cpu_time_per_day")
	if cpu_time and cpu_time > 0:
		return {"rate_limit": {"limit": cpu_time * 3600, "window": 86400}}
	return {}


def get_ones_without_offsite_backups() -> List[str]:
	return frappe.get_all(
		"Plan Attribute",
		filters={"fieldname": "offsite_backups", "value": "0"},
		pluck="parent",
	)


def plan_attribute(plan: str, attribute) -> Any:
	if isinstance(attribute, list):
		return [
			cast(attr["fieldtype"], attr["value"])
			for attr in frappe.get_all(
				"Plan Attribute",
				filters={"parent": plan, "fieldname": ("in", attribute)},
				fields=["fieldtype", "value"],
			)
		]

	fieldtype, value = frappe.db.get_value(
		"Plan Attribute", {"parent": plan, "fieldname": attribute}, ["fieldtype", "value"]
	)
	return cast(fieldtype, value)


@frappe.whitelist()
def get_plans(document_type, name, rg=None):
	filters = {"enabled": True, "document_type": document_type, "price_usd": (">", 0)}

	if document_type == "Site" and name or rg:
		team = get_current_team()
		release_group_name = rg if rg else frappe.db.get_value("Site", name, "group")
		release_group = frappe.get_doc("Release Group", release_group_name)
		is_private_bench = release_group.team == team and not release_group.public
		is_system_user = (
			frappe.db.get_value("User", frappe.session.user, "user_type") == "System User"
		)
		# poor man's bench paywall
		# this will not allow creation of $10 sites on private benches
		# wanted to avoid adding a new field, so doing this with a date check :)
		# TODO: find a better way to do paywalls
		paywall_date = frappe.utils.get_datetime("2021-09-21 00:00:00")
		is_paywalled_bench = (
			is_private_bench and release_group.creation > paywall_date and not is_system_user
		)
		if is_paywalled_bench:
			filters["private_benches"] = is_paywalled_bench

	plans = get_plans_with_attributes(filters)
	out = []
	for plan in plans:
		if frappe.utils.has_common([p["role"] for p in plan["roles"]], frappe.get_roles()):
			plan.pop("roles", "")
			out.append(plan)

	return out


def get_plans_with_attributes(filters):
	plans = frappe.qb.get_query(
		"Plan",
		fields=[
			"name",
			"plan_title",
			"price_usd",
			"price_inr",
			"enabled",
			{"roles": ["role"]},
			{"attributes": ["fieldname", "fieldtype", "value"]},
		],
		order_by="price_usd asc",
		filters=filters,
	).run(as_dict=1)

	for plan in plans:
		for attr in plan["attributes"]:
			attr_name = attr["fieldname"]
			attr_value = cast(attr["fieldtype"], attr["value"])

			# make a list if attributes with same fieldname
			if attr_name in plan:
				if isinstance(plan[attr_name], list):
					plan[attr_name].append(attr_value)
				else:
					plan[attr_name] = [plan[attr_name], attr_value]
			else:
				plan[attr_name] = attr_value

		del plan["attributes"]

	return plans
