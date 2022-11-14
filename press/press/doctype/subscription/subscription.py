# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from typing import List
from press.press.doctype.plan.plan import Plan

import frappe
from frappe.model.document import Document
from press.utils import log_error
from press.overrides import get_permission_query_conditions_for_doctype


class Subscription(Document):
	def validate(self):
		self.validate_duplicate()

	def on_update(self):
		doc = self.get_subscribed_document()
		plan_field = doc.meta.get_field("plan")
		if not (plan_field and plan_field.options == "Plan"):
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
		if not team.get_upcoming_invoice():
			team.create_upcoming_invoice()

		plan = frappe.get_cached_doc("Plan", self.plan)
		amount = plan.get_price_for_interval(self.interval, team.currency)

		usage_record = frappe.get_doc(
			doctype="Usage Record",
			team=self.team,
			document_type=self.document_type,
			document_name=self.document_name,
			plan=plan.name,
			amount=amount,
			subscription=self.name,
			interval=self.interval,
		)
		usage_record.insert()
		usage_record.submit()
		return usage_record

	def can_charge_for_subscription(self):
		doc = self.get_subscribed_document()
		if not doc:
			return False

		if hasattr(doc, "can_charge_for_subscription"):
			return doc.can_charge_for_subscription()

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
		results = frappe.db.get_all(
			"Subscription",
			{
				"team": self.team,
				"document_type": self.document_type,
				"document_name": self.document_name,
			},
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
	paid_plans = frappe.db.get_all(
		"Plan",
		{
			"document_type": ("in", ("Site", "Server", "Database Server")),
			"is_trial_plan": 0,
			"price_inr": (">", 0),
		},
		pluck="name",
		ignore_ifnull=True,
	)
	already_created = frappe.get_all(
		"Usage Record",
		filters={
			"document_type": ("in", ("Site", "Server", "Database Server")),
			"date": frappe.utils.today(),
		},
		pluck="subscription",
		ignore_ifnull=True,
	)
	subscriptions = frappe.db.get_all(
		"Subscription",
		filters={
			"enabled": True,
			"plan": ("in", paid_plans),
			"name": ("not in", already_created),
		},
		pluck="name",
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


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Subscription"
)
