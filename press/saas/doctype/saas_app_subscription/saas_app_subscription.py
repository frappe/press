# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.utils import log_error
from frappe.core.doctype.user.user import generate_keys


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

		response = generate_keys(site_doc.team)
		api_key = frappe.db.get_value("User", site_doc.team, "api_key")
		new_config = [
			{"key": "saas_api_key", "value": api_key, "type": "String"},
			{"key": "saas_api_secret", "value": response["api_secret"], "type": "String"},
			{"key": f"sk_{self.app}", "value": self.secret_key, "type": "String"},
		]

		if self.app == "erpnext_smb":
			new_config.append({"key": "plan", "value": "Free"})

		site_doc.update_site_config(new_config)

	def validate_saas_app_plan(self):
		app = frappe.db.get_value("Saas App Plan", self.saas_app_plan, "app")

		if app != self.app:
			frappe.throw(f"Plan {self.saas_app_plan} is not for app {frappe.bold(self.app)}!")

	def set_plan(self):
		self.plan = frappe.db.get_value("Saas App Plan", self.saas_app_plan, "plan")

	def change_plan(self, new_plan):
		self.saas_app_plan = new_plan["name"]
		self.save(ignore_permissions=True)

		site_doc = frappe.get_doc("Site", self.site)
		site_doc.change_plan(self.plan)

	def validate_duplicate_subscription(self):
		already_exists = frappe.db.exists(
			"Saas App Subscription", {"app": self.app, "site": self.site}
		)

		if already_exists:
			frappe.throw(
				f"Subscription for app '{frappe.bold(self.app)}' already exists for"
				f" site '{frappe.bold(self.site)}'!"
			)

	def create_usage_record(self):
		if self.is_usage_record_created():
			return

		team_name = frappe.db.get_value("Site", self.site, "team")
		team = frappe.get_cached_doc("Team", team_name)

		if not team.get_upcoming_invoice():
			team.create_upcoming_invoice()

		plan = frappe.get_cached_doc("Plan", self.plan)
		amount = plan.get_price_for_interval(self.interval, team.currency)
		payout_percentage = frappe.db.get_value(
			"Saas App Plan", self.saas_app_plan, "payout_percentage"
		)

		usage_record = frappe.get_doc(
			doctype="Usage Record",
			team=team_name,
			document_type="Saas App",
			document_name=self.app,
			plan=self.plan,
			amount=amount,
			subscription=self.name,
			interval=self.interval,
			payout=(amount / 100) * float(payout_percentage),
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


def create_usage_records():
	subscriptions = frappe.db.get_all(
		"Saas App Subscription", filters={"status": "Active"}, pluck="name"
	)
	for name in subscriptions:
		subscription = frappe.get_doc("Saas App Subscription", name)

		if not should_create_usage_record(subscription):
			continue

		try:
			subscription.create_usage_record()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Saas App: Create Usage Record Error", name=name)


def should_create_usage_record(subscription):
	# Don't create for free plans
	is_free = frappe.db.get_value("Saas App Plan", subscription.saas_app_plan, "is_free")

	if is_free:
		return False

	return True
