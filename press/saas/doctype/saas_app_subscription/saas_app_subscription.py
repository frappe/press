# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date
from press.utils import log_error
from datetime import datetime


class SaasAppSubscription(Document):
	def validate(self):
		self.set_secret_key()
		self.validate_saas_app_plan()
		self.set_plan()

	def set_secret_key(self):
		if not self.secret_key:
			from hashlib import blake2b

			h = blake2b(digest_size=20)
			h.update(self.name.encode())
			self.secret_key = h.hexdigest()

			self.create_site_config_key()

	def create_site_config_key(self):
		if not frappe.db.exists("Site Config Key", {"key": f"sk_{self.app}"}):
			frappe.get_doc(
				doctype="Site Config Key", internal=True, key=f"sk_{self.app}"
			).insert(ignore_permissions=True)

	def before_insert(self):
		self.validate_duplicate_subscription()

	def after_insert(self):
		self.set_secret_key_in_site_config()

	def set_secret_key_in_site_config(self):
		site_doc = frappe.get_doc("Site", self.site)

		new_config = [
			{"key": f"sk_{self.app}", "value": self.secret_key, "type": "String"},
		]

		if self.app == "erpnext_smb":
			new_config.extend(
				[
					{"key": "sk_email_delivery_service", "value": self.secret_key},
					{"key": "plan", "value": self.initial_plan or "Free"},
					{"key": "mail_login", "value": "example@gmail.com", "type": "String"},
					{"key": "mail_password", "value": "edjxok4jh7", "type": "String"},
					{"key": "mail_port", "value": 587, "type": "Number"},
					{"key": "mail_server", "value": "smtp.gmail.com", "type": "String"},
				]
			)

		site_doc.update_site_config(new_config)

	def validate_saas_app_plan(self):
		app = frappe.db.get_value("Saas App Plan", self.saas_app_plan, "app")

		if app != self.app:
			frappe.throw(f"Plan {self.saas_app_plan} is not for app {frappe.bold(self.app)}!")

	def set_plan(self):
		self.plan, self.site_plan = frappe.db.get_value(
			"Saas App Plan", self.saas_app_plan, ["plan", "site_plan"]
		)

	def change_plan(self, new_plan, ignore_card_setup=False):
		self.saas_app_plan = new_plan
		self.status = "Active"
		self.save(ignore_permissions=True)

		site_doc = frappe.get_doc("Site", self.site)
		site_doc.change_plan(self.site_plan, ignore_card_setup)

	def update_end_date(self, payment_option):
		days = 364 if payment_option == "Yearly" else 29
		self.end_date = add_to_date(self.end_date or datetime.today().date(), days=days)

	def validate_duplicate_subscription(self):
		already_exists = frappe.db.exists(
			"Saas App Subscription", {"app": self.app, "site": self.site}
		)

		if already_exists:
			frappe.throw(
				f"Subscription for app '{frappe.bold(self.app)}' already exists for"
				f" site '{frappe.bold(self.site)}'!"
			)

	def deactivate(self):
		self.status = "Inactive"
		self.save(ignore_permissions=True)
		frappe.get_doc("Site", self.site).deactivate()

	def activate(self):
		self.status = "Active"
		self.save(ignore_permissions=True)
		frappe.get_doc("Site", self.site).activate()

	def suspend(self):
		self.status = "Suspended"
		self.save(ignore_permissions=True)
		frappe.get_doc("Site", self.site).suspend()

	def disable(self):
		if self.status == "Disabled":
			return
		self.status = "Disabled"
		self.save(ignore_permissions=True)

	def calculate_payout(self, amount, saas_app_plan=None):
		# Amount of money that is supposed to be paidout to the developers
		saas_app_plan = saas_app_plan or self.saas_app_plan
		payout_percentage = frappe.db.get_value(
			"Saas App Plan", saas_app_plan, "payout_percentage"
		)
		return (amount / 100) * float(payout_percentage)

	def create_usage_record(self):
		if self.is_usage_record_created():
			return

		team_name = frappe.db.get_value("Site", self.site, "team")
		team = frappe.get_cached_doc("Team", team_name)

		if not team.get_upcoming_invoice():
			team.create_upcoming_invoice()

		plan = frappe.get_cached_doc("Plan", self.plan)
		amount = plan.get_price_for_interval(self.interval, team.currency)
		payout = self.calculate_payout(amount)

		usage_record = frappe.get_doc(
			doctype="Usage Record",
			team=team_name,
			document_type="Saas App",
			document_name=self.app,
			plan=self.plan,
			amount=amount,
			subscription=self.name,
			interval=self.interval,
			payout=payout,
		)
		usage_record.insert()
		usage_record.submit()
		return usage_record

	def is_usage_record_created(self):
		team = frappe.db.get_value("Site", self.site, "team")
		filters = {
			"team": team,
			"document_type": "Saas App",
			"document_name": self.app,
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


def suspend_prepaid_subscriptions():
	filters = [
		["end_date", "<", frappe.utils.today()],
		["end_date", "is", "set"],
		["status", "=", "Active"],
	]
	subscriptions = frappe.get_all("Saas App Subscription", filters=filters)
	for sub in subscriptions:
		subscription = frappe.get_doc("Saas App Subscription", sub.name)
		try:
			subscription.suspend()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback(
				"Saas Subscription: Cannot suspend prepaid subscription", subscription.name
			)


def create_usage_records():
	subscriptions = frappe.db.get_all(
		"Saas App Subscription",
		filters={"status": "Active", "end_date": ["is", "not set"]},
		pluck="name",
	)
	for sub in subscriptions:
		subscription = frappe.get_doc("Saas App Subscription", sub)

		if not should_create_usage_record(subscription):
			continue

		try:
			subscription.create_usage_record()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Saas App: Create Usage Record Error", name=sub)


def should_create_usage_record(subscription):
	# Don't create for free plans
	is_free = frappe.db.get_value("Saas App Plan", subscription.saas_app_plan, "is_free")

	if is_free:
		return False

	return True


def process_prepaid_saas_payment(event):
	from datetime import datetime

	payment_intent = event["data"]["object"]
	team = frappe.get_doc("Team", {"stripe_customer_id": payment_intent["customer"]})
	amount = payment_intent["amount"] / 100
	metadata = payment_intent.get("metadata")
	saas_plan = metadata.get("plan")
	plan = frappe.db.get_value("Saas App Plan", saas_plan, "plan")

	# change subscription
	sub = frappe.get_doc("Saas App Subscription", metadata.get("subscription"))
	sub.update_end_date(metadata.get("payment_option"))
	sub.change_plan(saas_plan, True)
	sub.reload()

	# create invoice
	payout = sub.calculate_payout(amount)
	due_date = datetime.fromtimestamp(payment_intent["created"])
	payment_id = payment_intent["id"]
	document_name = metadata.get("app")
	invoice = create_saas_invoice(
		team=team,
		amount=amount,
		payout=payout,
		document_name=document_name,
		due_date=due_date,
		plan=plan,
		payment_id=payment_id,
	)

	# there should only be one charge object
	charge = payment_intent["charges"]["data"][0]["id"]
	# update transaction amount, fee and exchange rate
	invoice.update_transaction_details(charge)
	invoice.submit()


def create_saas_invoice(
	team, due_date, amount, payout, document_name, plan, payment_id=None, status="Paid"
):
	invoice = frappe.get_doc(
		doctype="Invoice",
		team=team.name,
		type="Service",
		status=status,
		due_date=due_date,
		amount_paid=amount,
		amount_due=amount,
		stripe_payment_intent_id=payment_id,
		payout=payout,
	)
	invoice.append(
		"items",
		{
			"description": "Saas Prepaid Purchase",
			"document_type": "Saas App",
			"document_name": document_name,
			"plan": frappe.db.get_value("Plan", plan, "plan_title"),
			"quantity": 1,
			"rate": amount,
		},
	)
	invoice.insert()
	invoice.reload()

	return invoice
