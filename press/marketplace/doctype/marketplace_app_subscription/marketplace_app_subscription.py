# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe


from press.utils import log_error
from frappe.model.document import Document
from press.press.doctype.site.site import Site


class MarketplaceAppSubscription(Document):
	def validate(self):
		self.set_secret_key()
		# TODO: Validate Duplicate subscription

	def set_secret_key(self):
		if not self.secret_key:
			from hashlib import blake2b

			h = blake2b(digest_size=20)
			h.update(self.name.encode())
			self.secret_key = h.hexdigest()

	def after_insert(self):
		# TODO: Check if this key already exists
		# TODO: Make the config value internal
		self.set_secret_key_in_site_config()

	def set_secret_key_in_site_config(self):
		site_doc: Site = frappe.get_doc("Site", self.site)

		key = f"sk_{self.app}"
		value = self.secret_key
		config = {key: value}

		site_doc.update_site_config(config)

	def create_usage_record(self):
		if self.is_usage_record_created():
			return

		team_name = frappe.db.get_value("Site", self.site, "team")
		team = frappe.get_cached_doc("Team", team_name)

		if not team.get_upcoming_invoice():
			team.create_upcoming_invoice()

		plan_name = frappe.db.get_value("Marketplace App Plan", self.plan, "plan")
		plan = frappe.get_cached_doc("Plan", plan_name)
		amount = plan.get_price_for_interval(self.interval, team.currency)

		usage_record = frappe.get_doc(
			doctype="Usage Record",
			team=team_name,
			document_type="Marketplace App",
			document_name=self.app,
			plan=plan_name,
			amount=amount,
			subscription=self.name,
			interval=self.interval,
		)
		usage_record.insert()
		usage_record.submit()
		return usage_record

	def is_usage_record_created(self):
		team = frappe.db.get_value("Site", self.site, "team")
		plan_name = frappe.db.get_value("Marketplace App Plan", self.plan, "plan")
		filters = {
			"team": team,
			"document_type": "Marketplace App",
			"document_name": self.app,
			"subscription": self.name,
			"interval": self.interval,
			"plan": plan_name,
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

	@frappe.whitelist()
	def activate(self):
		if self.status == "Active":
			frappe.throw("Subscription is already active.")

		self.status = "Active"
		self.save()


def create_usage_records():
	subscriptions = frappe.db.get_all(
		"Marketplace App Subscription", filters={"status": "Active"}, pluck="name"
	)
	for name in subscriptions:
		subscription = frappe.get_doc("Marketplace App Subscription", name)

		if not should_create_usage_record(subscription):
			continue

		try:
			subscription.create_usage_record()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Marketplace App: Create Usage Record Error", name=name)


def should_create_usage_record(subscription: MarketplaceAppSubscription):
	# For annual prepaid plans
	plan_name = frappe.db.get_value("Marketplace App Plan", subscription.plan, "plan")
	plan_interval = frappe.db.get_value("Plan", plan_name, "interval")

	if plan_interval == "Annually":
		return False

	# For non-active sites
	site_status = frappe.db.get_value("Site", subscription.site, "status")
	if site_status not in ("Active", "Inactive"):
		return False

	return True


def process_prepaid_marketplace_payment(event):
	"""`event`: Stripe Event"""
	from datetime import datetime

	payment_intent = event["data"]["object"]
	team = frappe.get_doc("Team", {"stripe_customer_id": payment_intent["customer"]})
	amount = payment_intent["amount"] / 100
	metadata = payment_intent.get("metadata")

	invoice = frappe.get_doc(
		doctype="Invoice",
		team=team.name,
		type="Service",
		status="Paid",
		due_date=datetime.fromtimestamp(payment_intent["created"]),
		amount_paid=amount,
		amount_due=amount,
		stripe_payment_intent_id=payment_intent["id"],
	)
	invoice.append(
		"items",
		{
			"description": "Prepaid Credits",
			"document_type": "Marketplace App",
			"document_name": metadata.get("app"),
			"quantity": 1,
			"rate": amount,
		},
	)

	invoice.insert()
	invoice.reload()
	# there should only be one charge object
	charge = payment_intent["charges"]["data"][0]["id"]
	# update transaction amount, fee and exchange rate
	invoice.update_transaction_details(charge)
	invoice.submit()
