# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class Subscription(Document):
	def validate(self):
		self.validate_duplicate()

	def enable(self):
		self.enabled = True
		self.save()

	def disable(self):
		self.enabled = False
		self.save()

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
		if self.enabled:
			results = frappe.db.get_all(
				"Subscription",
				{
					"enabled": True,
					"team": self.team,
					"document_type": self.document_type,
					"document_name": self.document_name,
					"plan": self.plan,
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


def create_usage_records():
	"""
	Creates usage records for enabled Subscriptions
	"""
	subscriptions = frappe.db.get_all(
		"Subscription", filters={"enabled": True}, pluck="name"
	)
	for name in subscriptions:
		subscription = frappe.get_doc("Subscription", name)
		subscription.create_usage_record()
