# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
import json
import requests

from frappe.model.document import Document
from press.press.doctype.site.site import Site


class MarketplaceAppSubscription(Document):
	def validate(self):
		self.set_secret_key()
		self.validate_marketplace_app_plan()
		self.set_plan()

	def set_secret_key(self):
		if not self.secret_key:
			self.secret_key = frappe.generate_hash(length=40)
			self.create_site_config_key()

	def create_site_config_key(self):
		if not frappe.db.exists("Site Config Key", {"key": f"sk_{self.app}"}):
			frappe.get_doc(
				doctype="Site Config Key", internal=True, key=f"sk_{self.app}"
			).insert(ignore_permissions=True)

	def validate_marketplace_app_plan(self):
		app = frappe.db.get_value("Marketplace App Plan", self.marketplace_app_plan, "app")

		if app != self.app:
			frappe.throw(
				f"Plan {self.marketplace_app_plan} is not for app {frappe.bold(self.app)}!"
			)

	def set_plan(self):
		if not self.plan or self.has_value_changed("marketplace_app_plan"):
			self.plan = frappe.db.get_value(
				"Marketplace App Plan", self.marketplace_app_plan, "plan"
			)

	def validate_duplicate_subscription(self):
		if not self.site:
			return

		already_exists = frappe.db.exists(
			"Marketplace App Subscription", {"app": self.app, "site": self.site}
		)

		if already_exists:
			frappe.throw(
				f"Subscription for app '{frappe.bold(self.app)}' already exists for"
				f" site '{frappe.bold(self.site)}'!"
			)

	def before_insert(self):
		self.validate_duplicate_subscription()

	def on_update(self):
		if self.has_value_changed("marketplace_app_plan"):
			self.plan = frappe.db.get_value(
				"Marketplace App Plan", self.marketplace_app_plan, "plan"
			)
			frappe.db.set_value("Subscription", self.subscription, "plan", self.plan)

		if self.has_value_changed("team"):
			frappe.db.set_value("Subscription", self.subscription, "team", self.team)

		if self.has_value_changed("status"):
			frappe.db.set_value(
				"Subscription", self.subscription, "enabled", 1 if self.status == "Active" else 0
			)

	def after_insert(self):
		# TODO: Check if this key already exists
		if not self.while_site_creation:
			self.set_keys_in_site_config()

		subscription = frappe.get_doc(
			{
				"doctype": "Subscription",
				"team": self.team,
				"document_type": "Marketplace App",
				"document_name": self.app,
				"marketplace_app_subscription": self.name,
				"plan": frappe.get_value("Marketplace App Plan", self.marketplace_app_plan, "plan"),
			}
		).insert(ignore_permissions=True)
		self.subscription = subscription.name
		self.save()

		self.update_subscription_hook()

	def set_keys_in_site_config(self):
		site_doc: Site = frappe.get_doc("Site", self.site)

		key_id = f"sk_{self.app}"
		secret_key = self.secret_key

		old_config = [
			{"key": x.key, "value": x.value, "type": x.type}
			for x in list(filter(lambda x: not x.internal, site_doc.configuration))
		]
		config = [
			{"key": key_id, "value": secret_key, "type": "String"},
			{
				"key": "subscription",
				"value": {"secret_key": secret_key},
				"type": "JSON",
			},
		]
		if "prepaid" == frappe.db.get_value(
			"Saas Settings", self.app, "billing_type"
		) and frappe.db.get_value("Site", self.site, "trial_end_date"):
			config.append(
				{
					"key": "app_include_js",
					"value": [frappe.db.get_single_value("Press Settings", "app_include_script")],
					"type": "JSON",
				}
			)

		config = config + old_config

		expiry = frappe.db.get_value("Site", self.site, "trial_end_date")
		if expiry:
			config[1]["value"].update({"expiry": str(expiry)})

		site_doc.update_site_config(config)

	@frappe.whitelist()
	def activate(self):
		if self.status == "Active":
			frappe.throw("Subscription is already active.")

		self.status = "Active"
		self.save()

	def disable(self):
		if self.status == "Disabled":
			return
		self.status = "Disabled"
		self.save(ignore_permissions=True)
		frappe.db.set_value("Subscription", self.subscription, "enabled", 0)

	def update_subscription_hook(self):
		# sends app name and plan whenever a subscription is created for other apps
		# this can be used for activating and deactivating workspaces
		if self.app in ["erpnext", "hrms"]:
			paths = frappe.get_list(
				"Marketplace App",
				{"subscription_update_hook": ("is", "set")},
				pluck="subscription_update_hook",
			)
			try:
				for path in paths:
					requests.post(
						f"https://{self.site}/api/method/{path}",
						data={"app": self.app, "plan": self.plan},
					)
			except Exception:
				pass
		else:
			return


def process_prepaid_marketplace_payment(event):
	"""`event`: Stripe Event"""
	from datetime import datetime

	payment_intent = event["data"]["object"]
	team = frappe.get_doc("Team", {"stripe_customer_id": payment_intent["customer"]})
	amount = payment_intent["amount"] / 100
	metadata = payment_intent.get("metadata")
	site = metadata.get("site")

	invoice = frappe.get_doc(
		doctype="Invoice",
		team=team.name,
		type="Prepaid Credits",
		status="Paid",
		marketplace=1,
		due_date=datetime.fromtimestamp(payment_intent["created"]),
		amount_paid=amount,
		amount_due=amount,
		stripe_payment_intent_id=payment_intent["id"],
	)

	invoice_line_items = []
	total_hosting_cost = 0.0
	for line_item in json.loads(metadata.get("line_items")):
		app = line_item["app"]
		title = frappe.db.get_value("Marketplace App", app, "title")
		plan = line_item["plan"]
		subscription = line_item["subscription"]

		if subscription == "new":
			# create new subscription and install apps
			frappe.get_doc(
				{
					"doctype": "Marketplace App Subscription",
					"app": app,
					"team": team.name,
					"site": site,
					"marketplace_app_plan": plan,
				}
			).insert(ignore_permissions=True)
			install_subscription_apps(site, app)
		else:
			# Update plan on subscription
			marketplace_subscription = frappe.get_doc(
				"Marketplace App Subscription", subscription
			)
			marketplace_subscription.marketplace_app_plan = plan
			marketplace_subscription.save(ignore_permissions=True)

		hosting_amount = change_site_hosting_plan(site, plan, team)
		invoice_line_items.append(
			{
				"description": f"Prepaid Credits for {title}",
				"document_type": "Marketplace App",
				"document_name": app,
				"plan": frappe.db.get_value("Marketplace App Plan", plan, "plan"),
				"rate": float(line_item["amount"]) - hosting_amount,
				"quantity": float(line_item["quantity"]),
			}
		)
		total_hosting_cost += hosting_amount

	# Add hosting as separate line item
	invoice_line_items.append(
		{
			"description": "Frappe Cloud Hosting",
			"document_type": "Site",
			"document_name": site,
			"rate": float(total_hosting_cost),
			"quantity": 1,
		}
	)
	for line_item in invoice_line_items:
		invoice.append("items", line_item)

	invoice.insert()
	invoice.reload()
	# there should only be one charge object
	charge = payment_intent["charges"]["data"][0]["id"]
	# update transaction amount, fee and exchange rate
	invoice.update_transaction_details(charge)
	invoice.submit()

	team.allocate_credit_amount(
		float(metadata.get("credits")), source="Prepaid Credits", remark=payment_intent["id"]
	)


def change_site_hosting_plan(site, plan, team):
	# Compare site hosting plan with new hosting plan and set max hosting_plan for site
	standard_hosting_plan = frappe.db.get_value(
		"Marketplace App Plan", plan, "standard_hosting_plan"
	)
	hosting_amount = frappe.db.get_value(
		"Plan", standard_hosting_plan, f"price_{team.currency.lower()}"
	)
	site_plan = frappe.db.get_value("Site", site, "plan")
	site_plan_value = frappe.db.get_value(
		"Plan", site_plan, f"price_{team.currency.lower()}"
	)
	if hosting_amount > site_plan_value:
		# set new site plan as new standard_hosting_plan, since it is higher
		frappe.get_doc("Site", site).change_plan(standard_hosting_plan)

	return hosting_amount


def install_subscription_apps(site, app):
	site_doc = frappe.get_doc("Site", site)

	for app in set(frappe.get_all("ERPNext App", {"parent": app}, pluck="app")).difference(
		{sa.app for sa in site_doc.apps}
	):
		site_doc.install_app(app)


def get_login_url(secret_key):
	from frappe.utils import get_url

	return get_url(
		f"/api/method/press.api.developer.marketplace.get_login_url?secret_key={secret_key}"
	)
