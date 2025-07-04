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
		"""We will sometime send plans that are not enabled, since database conversions were not
		done region wise, we will need to allow plan change for both arm and intel however creation
		of new intel servers can be stopped by keeping intel plans disabled.
		"""
		filters = filters or {}
		if not fields:
			fields = ["*"]

		fields.append("`tabHas Role`.role")
		filters.update({"enabled": True})
		plans = frappe.get_all(doctype, filters=filters, fields=fields, order_by="price_usd asc")
		return filter_by_roles(plans)


def filter_by_roles(plans):
	plans = group_children_in_result(plans, {"role": "roles"})

	out = []
	for plan in plans:
		if frappe.utils.has_common(plan["roles"], frappe.get_roles()):
			plan.pop("roles", "")
			out.append(plan)

	return out
