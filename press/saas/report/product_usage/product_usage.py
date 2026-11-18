# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Date, Sum
from frappe.utils import add_days, get_datetime, today

# Sites that customers use now. Updating and Recovering sites go back to Active.
LIVE_SITE_STATUSES = ("Active", "Updating", "Recovering")
CHART_APPS = 5
NUMBER_FIELDS = {
	"active_installs": "Active Installs",
	"paid_installs": "Paid",
	"trial_installs": "Trial",
	"free_installs": "Free",
	"new_installs": "New Installs",
	"signups": "Sign-ups",
	"sites_created": "Sites Created",
	"setup_complete": "Setup Complete",
}


def execute(filters=None):
	usage = ProductUsage(frappe._dict(filters or {}))
	rows = usage.get_rows()
	return get_columns(), rows, None, usage.get_chart(rows), get_summary(rows)


class ProductUsage:
	"""Counts of installs and sign-ups per app. It shows no site, team or user."""

	def __init__(self, filters: frappe._dict):
		self.from_date = get_datetime(filters.from_date or add_days(today(), -30))
		self.to_date = get_datetime(add_days(filters.to_date or today(), 1))
		self.apps = get_product_apps() if filters.product_apps_only else None
		self.site = frappe.qb.DocType("Site")
		self.site_app = frappe.qb.DocType("Site App")
		self.daily_installs = self.get_daily_installs()

	def get_rows(self) -> list[frappe._dict]:
		rows: dict[str, frappe._dict] = {}
		for counts in (self.get_installs(), self.get_new_installs(), self.get_signups()):
			for app, values in counts.items():
				rows.setdefault(app, frappe._dict(app=app, **dict.fromkeys(NUMBER_FIELDS, 0))).update(values)
		return sorted(rows.values(), key=lambda row: (-row["active_installs"], row["app"]))

	def get_installs(self) -> dict[str, dict]:
		"""Installs on live sites, split into paid, trial and free plans."""
		SitePlan = frappe.qb.DocType("Site Plan")
		is_trial = SitePlan.is_trial_plan == 1
		is_paid = (SitePlan.is_trial_plan == 0) & (self.site.free == 0) & (SitePlan.price_usd > 0)
		query = (
			self.site_app_query()
			.left_join(SitePlan)
			.on(SitePlan.name == self.site.plan)
			.select(
				self.site_app.app,
				Count("*").as_("active_installs"),
				Sum(Case().when(is_paid, 1).else_(0)).as_("paid_installs"),
				Sum(Case().when(is_trial, 1).else_(0)).as_("trial_installs"),
			)
			.where(self.site.status.isin(LIVE_SITE_STATUSES))
			.groupby(self.site_app.app)
		)
		return {row.pop("app"): with_free_installs(as_counts(row)) for row in query.run(as_dict=True)}

	def get_new_installs(self) -> dict[str, dict]:
		counts: dict[str, dict] = {}
		for row in self.daily_installs:
			counts.setdefault(row["app"], {"new_installs": 0})["new_installs"] += row["installs"]
		return counts

	def get_daily_installs(self) -> list[frappe._dict]:
		"""Apps installed in the date range, on sites of any status, per day."""
		day = Date(self.site_app.creation)
		return (
			self.site_app_query()
			.select(self.site_app.app, day.as_("day"), Count("*").as_("installs"))
			.where(self.site_app.creation >= self.from_date)
			.where(self.site_app.creation < self.to_date)
			.groupby(self.site_app.app, day)
			.run(as_dict=True)
		)

	def get_signups(self) -> dict[str, dict]:
		"""Sign-ups in the date range, counted for each app of the product."""
		Request = frappe.qb.DocType("Product Trial Request")
		TrialApp = frappe.qb.DocType("Product Trial App")
		query = (
			frappe.qb.from_(Request)
			.join(TrialApp)
			.on((TrialApp.parent == Request.product_trial) & (TrialApp.parenttype == "Product Trial"))
			.left_join(self.site)
			.on(self.site.name == Request.site)
			.select(
				TrialApp.app,
				Count("*").as_("signups"),
				Sum(Case().when(Request.status == "Site Created", 1).else_(0)).as_("sites_created"),
				Sum(Case().when(self.site.setup_wizard_complete == 1, 1).else_(0)).as_("setup_complete"),
			)
			.where(Request.creation >= self.from_date)
			.where(Request.creation < self.to_date)
			.groupby(TrialApp.app)
		)
		if self.apps is not None:
			query = query.where(TrialApp.app.isin(self.apps or [""]))
		return {row.pop("app"): as_counts(row) for row in query.run(as_dict=True)}

	def site_app_query(self):
		"""Site App rows of sites that are not in a standby pool."""
		query = (
			frappe.qb.from_(self.site_app)
			.join(self.site)
			.on((self.site.name == self.site_app.parent) & (self.site_app.parenttype == "Site"))
			.where(self.site.is_standby == 0)
		)
		if self.apps is not None:
			query = query.where(self.site_app.app.isin(self.apps or [""]))
		return query

	def get_chart(self, rows: list[frappe._dict]) -> dict:
		"""New installs per week of the apps with the most new installs."""
		top_rows = sorted((row for row in rows if row["new_installs"]), key=lambda row: -row["new_installs"])
		weeks: dict[str, dict[str, int]] = {row["app"]: {} for row in top_rows[:CHART_APPS]}
		for row in self.daily_installs:
			if row["app"] in weeks:
				week = str(add_days(row["day"], -row["day"].weekday()))
				weeks[row["app"]][week] = weeks[row["app"]].get(week, 0) + row["installs"]

		labels = sorted({week for counts in weeks.values() for week in counts})
		datasets = [
			{"name": app, "values": [counts.get(week, 0) for week in labels]} for app, counts in weeks.items()
		]
		return {"data": {"labels": labels, "datasets": datasets}, "type": "line"}


def get_product_apps() -> list[str]:
	return frappe.get_all("Product Trial App", {"parenttype": "Product Trial"}, pluck="app", distinct=True)


def as_counts(row: frappe._dict) -> frappe._dict:
	"""SUM returns a decimal, or NULL for no rows."""
	return frappe._dict({field: int(value or 0) for field, value in row.items()})


def with_free_installs(row: frappe._dict) -> frappe._dict:
	row["free_installs"] = row["active_installs"] - row["paid_installs"] - row["trial_installs"]
	return row


def get_columns() -> list[dict]:
	app = {"fieldname": "app", "label": _("App"), "fieldtype": "Link", "options": "App", "width": 180}
	counts = [
		{"fieldname": field, "label": _(label), "fieldtype": "Int", "width": 120}
		for field, label in NUMBER_FIELDS.items()
	]
	return [app, *counts]


def get_summary(rows: list[frappe._dict]) -> list[dict]:
	"""Totals over the apps. A site with two of the apps counts twice."""
	cards = {
		"active_installs": ("Active Installs", "blue"),
		"paid_installs": ("Paid Installs", "green"),
		"new_installs": ("New Installs", "blue"),
		"signups": ("Sign-ups", "orange"),
	}
	return [
		{"value": sum(row[field] for row in rows), "label": _(label), "datatype": "Int", "indicator": color}
		for field, (label, color) in cards.items()
	]
