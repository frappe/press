import frappe
from frappe.model.document import Document
from frappe.utils import rounded

from press.utils import group_children_in_result


class Plan(Document):
	def get_price_for_interval(self, interval, currency):
		price_per_day = self.get_price_per_day(currency)

		if interval == "Daily":
			return price_per_day

		if interval == "Monthly":
			return rounded(price_per_day * 30)

		return None

	def get_price_per_day(self, currency):
		price = self.price_inr if currency == "INR" else self.price_usd
		return rounded(price / self.period, 2)

	@property
	def period(self):
		return frappe.utils.get_last_day(None).day

	@classmethod
	def get_plans(cls, doctype, fields=None, filters=None):
		or_filters = None
		filters = filters or {}
		if not fields:
			fields = ["*"]

		# Should either be enabled or a legacy plan
		# In case a platform is not passed in we want more control and only want to show
		# enabled plans in the region, in other cases we can show legacy plan
		if doctype != "Server Plan" or not filters.get("platform"):
			filters.update({"enabled": True})
		else:
			or_filters = {"enabled": True, "legacy_plan": True}

		fields.append("`tabHas Role`.role")
		plans = frappe.get_all(
			doctype, filters=filters, fields=fields, order_by="price_usd asc", or_filters=or_filters
		)
		return filter_by_roles(plans)


def filter_by_roles(plans):
	plans = group_children_in_result(plans, {"role": "roles"})

	out = []
	for plan in plans:
		if frappe.utils.has_common(plan["roles"], frappe.get_roles()):
			plan.pop("roles", "")
			out.append(plan)

	return out
