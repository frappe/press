# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, cast

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Coalesce, Count, Date, Sum
from frappe.utils import add_days, get_datetime, getdate, today

if TYPE_CHECKING:
	from datetime import date

# Sites that customers use now. Updating and Recovering sites go back to Active.
LIVE_SITE_STATUSES = ("Active", "Updating", "Recovering")
CHART_APPS = 5


def execute(filters=None):
	usage = ProductUsage(frappe._dict(filters or {}))
	rows = usage.get_rows()
	return get_columns(), rows, None, usage.get_chart(rows), usage.get_summary()


class ProductUsage:
	"""Counts of installs and sign-ups per app. It shows no site, team or user."""

	def __init__(self, filters: frappe._dict):
		self.from_date = as_date(filters.from_date or add_days(today(), -30))
		self.to_date = as_date(filters.to_date or today())
		self.start = get_datetime(self.from_date)
		self.end = get_datetime(add_days(self.to_date, 1))
		self.product_apps_only = bool(filters.product_apps_only)
		self.site = frappe.qb.DocType("Site")
		self.site_app = frappe.qb.DocType("Site App")
		self.request = frappe.qb.DocType("Product Trial Request")
		# A claimed standby site starts at sign-up, not when the pool made it
		self.site_start = Coalesce(self.site.signup_time, self.site.creation)

	@cached_property
	def apps(self) -> list[str] | None:
		return get_product_apps() if self.product_apps_only else None

	def get_rows(self) -> list[frappe._dict]:
		empty = dict.fromkeys(COUNT_FIELDS, 0)
		rows: dict[str, frappe._dict] = {}
		for counts in (self.get_installs(), self.get_new_installs(), self.get_signups()):
			for app, values in counts.items():
				rows.setdefault(app, frappe._dict(app=app, **empty)).update(values)
		return sorted(rows.values(), key=lambda row: (-row["active_installs"], row["app"]))

	def get_installs(self) -> dict[str, dict]:
		"""Installs on live sites, split into paid, trial and free plans."""
		SitePlan = frappe.qb.DocType("Site Plan")
		is_trial = SitePlan.is_trial_plan == 1
		# A free site on a trial plan counts as trial. No plan counts as free.
		has_price = (SitePlan.price_usd > 0) | (SitePlan.price_inr > 0)
		is_paid = (SitePlan.is_trial_plan == 0) & (self.site.free == 0) & has_price
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

	@cached_property
	def daily_installs(self) -> list[dict]:
		"""Installs per app and day: the apps of new sites, and apps added later to older sites."""
		return self.get_new_site_installs() + self.get_later_installs()

	def get_new_site_installs(self) -> list[dict]:
		"""Site App rows only take the creation of their site, so count by site start."""
		day = Date(self.site_start)
		return (
			self.site_app_query()
			.select(self.site_app.app, day.as_("day"), Count("*").as_("installs"))
			.where(self.site_start >= self.start)
			.where(self.site_start < self.end)
			.groupby(self.site_app.app, day)
			.run(as_dict=True)
		)

	def get_later_installs(self) -> list[dict]:
		Activity = frappe.qb.DocType("Site Activity")
		day = Date(Activity.creation)
		query = (
			frappe.qb.from_(Activity)
			.join(self.site)
			.on(self.site.name == Activity.site)
			.select(Activity.reason.as_("app"), day.as_("day"), Count("*").as_("installs"))
			.where(Activity.action == "Install App")
			.where(Activity.creation >= self.start)
			.where(Activity.creation < self.end)
			.where(self.site_start < self.start)
			.groupby(Activity.reason, day)
		)
		if self.apps is not None:
			query = query.where(Activity.reason.isin(self.apps or [""]))
		return query.run(as_dict=True)

	def get_signups(self) -> dict[str, dict]:
		"""Sign-ups for each app of the product that the user signed up for."""
		TrialApp = frappe.qb.DocType("Product Trial App")
		query = (
			self.signup_query()
			.join(TrialApp)
			.on((TrialApp.parent == self.request.product_trial) & (TrialApp.parenttype == "Product Trial"))
			.select(TrialApp.app)
			.groupby(TrialApp.app)
		)
		if self.apps is not None:
			query = query.where(TrialApp.app.isin(self.apps or [""]))
		return {row.pop("app"): as_counts(row) for row in query.run(as_dict=True)}

	def get_summary(self) -> list[dict]:
		"""Sign-ups of all products. Install totals are left out: a site has more than one app."""
		totals = as_counts(self.signup_query().run(as_dict=True)[0])
		return [
			{"value": totals.signups, "label": _("Sign-ups"), "datatype": "Int", "indicator": "blue"},
			{
				"value": totals.sites_created,
				"label": _("Sites Created"),
				"datatype": "Int",
				"indicator": "green",
			},
			{
				"value": totals.setup_complete,
				"label": _("Setup Complete"),
				"datatype": "Int",
				"indicator": "green",
			},
		]

	def signup_query(self):
		return (
			frappe.qb.from_(self.request)
			.left_join(self.site)
			.on(self.site.name == self.request.site)
			.select(
				Count("*").as_("signups"),
				Sum(Case().when(self.request.status == "Site Created", 1).else_(0)).as_("sites_created"),
				Sum(Case().when(self.site.setup_wizard_complete == 1, 1).else_(0)).as_("setup_complete"),
			)
			.where(self.request.creation >= self.start)
			.where(self.request.creation < self.end)
		)

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
		labels = get_weeks(self.from_date, self.to_date)
		weeks: dict[str, dict[str, int]] = {
			row["app"]: dict.fromkeys(labels, 0) for row in top_rows[:CHART_APPS]
		}
		for row in self.daily_installs:
			if row["app"] in weeks:
				weeks[row["app"]][str(get_week(as_date(row["day"])))] += row["installs"]

		datasets = [{"name": app, "values": list(counts.values())} for app, counts in weeks.items()]
		return {"data": {"labels": labels, "datasets": datasets}, "type": "line"}


def get_product_apps() -> list[str]:
	"""Apps of Product Trials, without frappe, which every product has."""
	TrialApp = frappe.qb.DocType("Product Trial App")
	App = frappe.qb.DocType("App")
	return (
		frappe.qb.from_(TrialApp)
		.join(App)
		.on(App.name == TrialApp.app)
		.select(TrialApp.app)
		.distinct()
		.where(TrialApp.parenttype == "Product Trial")
		.where(App.frappe == 0)
		.run(pluck=True)
	)


def get_weeks(from_date: date, to_date: date) -> list[str]:
	"""The Monday of each week in the range, also the weeks without installs."""
	week, weeks = get_week(from_date), []
	while week <= to_date:
		weeks.append(str(week))
		week = as_date(add_days(week, 7))
	return weeks


def get_week(day: date) -> date:
	return as_date(add_days(day, -day.weekday()))


def as_date(value) -> date:
	return cast("date", getdate(value))


def as_counts(row: dict) -> frappe._dict:
	"""SUM returns a decimal, or NULL for no rows."""
	return frappe._dict({field: int(value or 0) for field, value in row.items()})


def with_free_installs(row: frappe._dict) -> frappe._dict:
	row["free_installs"] = row["active_installs"] - row["paid_installs"] - row["trial_installs"]
	return row


COUNT_FIELDS = (
	"active_installs",
	"paid_installs",
	"trial_installs",
	"free_installs",
	"new_installs",
	"signups",
	"sites_created",
	"setup_complete",
)


def get_columns() -> list[dict]:
	labels = (
		_("Active Installs"),
		_("Paid"),
		_("Trial"),
		_("Free"),
		_("New Installs"),
		_("Sign-ups"),
		_("Sites Created"),
		_("Setup Complete"),
	)
	# Data, not Link: Press Product Manager cannot read App
	app = {"fieldname": "app", "label": _("App"), "fieldtype": "Data", "width": 180}
	counts = [
		{"fieldname": field, "label": label, "fieldtype": "Int", "width": 120}
		for field, label in zip(COUNT_FIELDS, labels, strict=True)
	]
	return [app, *counts]
