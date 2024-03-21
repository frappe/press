# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from typing import List

from frappe.query_builder.functions import Coalesce, Count
from press.press.doctype.plan.plan import Plan

import frappe
from frappe.model.document import Document
from press.utils import log_error
from press.overrides import get_permission_query_conditions_for_doctype


class Subscription(Document):
	dashboard_fields = [
		"site",
		"enabled",
		"document_type",
		"document_name",
		"team",
	]

	@staticmethod
	def get_list_query(query, **list_args):
		Subscription = frappe.qb.DocType("Subscription")
		UsageRecord = frappe.qb.DocType("Usage Record")
		Plan = frappe.qb.DocType("Marketplace App Plan")
		price_field = (
			Plan.price_inr if frappe.local.team().currency == "INR" else Plan.price_usd
		)

		query = (
			frappe.qb.from_(Subscription)
			.join(Plan)
			.on(Subscription.plan == Plan.name)
			.left_join(UsageRecord)
			.on(UsageRecord.subscription == Subscription.name)
			.groupby(Subscription.name)
			.select(
				Subscription.site,
				Subscription.enabled,
				price_field.as_("price"),
				Coalesce(Count(UsageRecord.subscription), 0).as_("active_for"),
			)
			.where(
				(Subscription.document_type == "Marketplace App")
				& (Subscription.document_name == list_args["filters"]["document_name"])
				& (Subscription.site != "")
				& (price_field > 0)
			)
			.limit(list_args["limit"])
		)

		return query.run(as_dict=True)

	def validate(self):
		self.validate_duplicate()

	def on_update(self):
		doc = self.get_subscribed_document()
		plan_field = doc.meta.get_field("plan")
		if not (
			plan_field
			and plan_field.options in ["Site Plan", "Server Plan", "Marketplace App Plan"]
		):
			return

		if self.enabled and doc.plan != self.plan:
			doc.plan = self.plan
			doc.save()
		if not self.enabled and doc.plan:
			doc.plan = ""
			doc.save()

	def enable(self):
		try:
			self.enabled = True
			self.save()
		except Exception:
			frappe.log_error(title="Enable Subscription Error")

	def disable(self):
		try:
			self.enabled = False
			self.save()
		except Exception:
			frappe.log_error(title="Disable Subscription Error")

	@frappe.whitelist()
	def create_usage_record(self):
		cannot_charge = not self.can_charge_for_subscription()
		if cannot_charge:
			return

		if self.is_usage_record_created():
			return

		team = frappe.get_cached_doc("Team", self.team)

		if team.parent_team:
			team = frappe.get_cached_doc("Team", team.parent_team)

		if team.billing_team and team.payment_mode == "Paid By Partner":
			team = frappe.get_cached_doc("Team", team.billing_team)

		if not team.get_upcoming_invoice():
			team.create_upcoming_invoice()

		plan = frappe.get_cached_doc(self.plan_type, self.plan)
		amount = plan.get_price_for_interval(self.interval, team.currency)

		usage_record = frappe.get_doc(
			doctype="Usage Record",
			team=team.name,
			document_type=self.document_type,
			document_name=self.document_name,
			plan_type=self.plan_type,
			plan=plan.name,
			amount=amount,
			subscription=self.name,
			interval=self.interval,
			site=(
				self.site
				or frappe.get_value(
					"Marketplace App Subscription", self.marketplace_app_subscription, "site"
				)
			)
			if self.document_type == "Marketplace App"
			else None,
		)
		usage_record.insert()
		usage_record.submit()
		return usage_record

	def can_charge_for_subscription(self):
		doc = self.get_subscribed_document()
		if not doc:
			return False

		if hasattr(doc, "can_charge_for_subscription"):
			return doc.can_charge_for_subscription(self)

		return True

	def is_usage_record_created(self):
		filters = {
			"team": self.team,
			"document_type": self.document_type,
			"document_name": self.document_name,
			"subscription": self.name,
			"interval": self.interval,
			"plan": self.plan,
		}

		if self.interval == "Daily":
			filters.update({"date": frappe.utils.today()})

		if self.interval == "Monthly":
			date = frappe.utils.getdate()
			first_day = frappe.utils.get_first_day(date)
			last_day = frappe.utils.get_last_day(date)
			filters.update({"date": ("between", (first_day, last_day))})

		result = frappe.db.get_all("Usage Record", filters=filters, limit=1)
		return bool(result)

	def validate_duplicate(self):
		if not self.is_new():
			return
		filters = {
			"team": self.team,
			"document_type": self.document_type,
			"document_name": self.document_name,
		}
		if self.document_type == "Marketplace App":
			filters.update({"marketplace_app_subscription": self.marketplace_app_subscription})

		results = frappe.db.get_all(
			"Subscription",
			filters,
			pluck="name",
			limit=1,
		)
		if results:
			link = frappe.utils.get_link_to_form("Subscription", results[0])
			frappe.throw(f"A Subscription already exists: {link}", frappe.DuplicateEntryError)

	def get_subscribed_document(self):
		if not hasattr(self, "_subscribed_document"):
			self._subscribed_document = frappe.get_doc(self.document_type, self.document_name)
		return self._subscribed_document

	@classmethod
	def get_sites_without_offsite_backups(cls) -> List[str]:
		plans = Plan.get_ones_without_offsite_backups()
		return frappe.get_all(
			"Subscription",
			filters={"document_type": "Site", "plan": ("in", plans)},
			pluck="document_name",
		)


def create_usage_records():
	"""
	Creates daily usage records for paid Subscriptions
	"""
	free_sites = sites_with_free_hosting()
	subscriptions = frappe.db.get_all(
		"Subscription",
		filters={
			"enabled": True,
			"plan": ("in", paid_plans()),
			"name": ("not in", created_usage_records(free_sites)),
			"document_name": ("not in", free_sites),
		},
		pluck="name",
		order_by=None,
		limit=2000,
	)
	for name in subscriptions:
		subscription = frappe.get_cached_doc("Subscription", name)
		try:
			subscription.create_usage_record()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Create Usage Record Error", name=name)


def paid_plans():
	paid_plans = []
	filter = {
		"price_inr": (">", 0),
		"enabled": 1,
	}
	doctypes = ["Site Plan", "Marketplace App Plan", "Server Plan"]
	for doctype in doctypes:
		paid_plans += frappe.get_all(doctype, filter, pluck="name", ignore_ifnull=True)

	return list(set(paid_plans))


def sites_with_free_hosting():
	# sites marked as free
	free_teams = frappe.get_all(
		"Team", filters={"free_account": True, "enabled": True}, pluck="name"
	)
	free_team_sites = frappe.get_all(
		"Site",
		{"status": ("not in", ("Archived", "Suspended")), "team": ("in", free_teams)},
		pluck="name",
	)
	return free_team_sites + frappe.get_all(
		"Site",
		filters={
			"free": True,
			"status": ("not in", ("Archived", "Suspended")),
			"team": ("not in", free_teams),
		},
		pluck="name",
	)


def created_usage_records(free_sites, date=None):
	date = date or frappe.utils.today()
	"""Returns created usage records for a particular date"""
	return frappe.get_all(
		"Usage Record",
		filters={
			"document_type": (
				"in",
				("Site", "Server", "Database Server", "Self Hosted Server", "Marketplace App"),
			),
			"date": date,
			"document_name": ("not in", free_sites),
		},
		pluck="subscription",
		orderby=None,
		ignore_ifnull=True,
	)


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Subscription"
)
