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

	def get_price_per_day(self, currency):
		price = self.price_inr if currency == "INR" else self.price_usd
		price_per_day = rounded(price / self.period, 2)
		return price_per_day

	@property
	def period(self):
		return frappe.utils.get_last_day(None).day

	@classmethod
	def get_plans(cls, doctype, fields=["*"], filters=None):
		filters = filters or {}
		fields.append("`tabHas Role`.role")
		filters.update({"enabled": True})
		plans = frappe.get_all(
			doctype, filters=filters, fields=fields, order_by="price_usd asc"
		)
		plans = filter_by_roles(plans)

		return plans


def filter_by_roles(plans):
	plans = group_children_in_result(plans, {"role": "roles"})

	out = []
	for plan in plans:
		if frappe.utils.has_common(plan["roles"], frappe.get_roles()):
			plan.pop("roles", "")
			out.append(plan)

	return out
