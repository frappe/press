# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_fullname
from hashlib import blake2b
from press.utils import log_error
from frappe.model.document import Document
from press.exceptions import FrappeioServerNotSet
from press.press.doctype.account_request.account_request import AccountRequest
from press.press.doctype.team.team import Team
from frappe.contacts.address_and_contact import load_address_and_contact
from press.utils.billing import (
	get_frappe_io_connection,
	get_stripe,
)


class Org(Document):
	def onload(self):
		load_address_and_contact(self)

	def validate(self):
		self.set_org_currency()
		self.set_billing_name()
		self.set_partner_email()

	def on_update(self):
		self.validate_payment_mode()
		self.update_draft_invoice_payment_mode()

		if not self.is_new() and self.billing_name:
			if self.has_value_changed("billing_name"):
				self.update_billing_details_on_frappeio()

	def before_insert(self):
		if not self.referrer_id:
			self.set_referrer_id()

		self.set_partner_payment_mode()

	def set_partner_payment_mode(self):
		if self.erpnext_partner:
			self.payment_mode = "Partner Credits"

	def set_referrer_id(self):
		h = blake2b(digest_size=4)
		h.update(self.name.encode())
		self.referrer_id = h.hexdigest()

	@classmethod
	def create_new(
		cls,
		account_request: AccountRequest,
		first_name: str,
		last_name: str,
		password: str = None,
		country: str = None,
		is_us_eu: bool = False,
		via_erpnext: bool = False,
		user_exists: bool = False,
	):
		"""Create new team along with user (user created first)."""
		org = frappe.get_doc(
			{
				"doctype": "Org",
				"name": account_request.team,
				"user": account_request.email,
				"country": country,
				"enabled": 1,
				"via_erpnext": via_erpnext,
				"is_us_eu": is_us_eu,
			}
		)

		if not user_exists:
			user = org.create_user(
				first_name, last_name, account_request.email, password, account_request.role
			)
		else:
			user = frappe.get_doc("User", account_request.email)
			user.append_roles(account_request.role)
			user.save(ignore_permissions=True)

		org.append("members", {"user": user.name})
		org.insert()

		org.create_stripe_customer()
		Team.create_new(account_request)
		return org

	@staticmethod
	def create_user(first_name=None, last_name=None, email=None, password=None, role=None):
		user = frappe.new_doc("User")
		user.first_name = first_name
		user.last_name = last_name
		user.email = email
		user.owner = email
		user.new_password = password
		user.append_roles(role)
		user.flags.no_welcome_mail = True
		user.save(ignore_permissions=True)
		return user

	def create_stripe_customer(self):
		if not self.stripe_customer_id:
			stripe = get_stripe()
			customer = stripe.Customer.create(email=self.user, name=get_fullname(self.user))
			self.stripe_customer_id = customer.id
			self.save()

	def update_draft_invoice_payment_mode(self):
		if self.has_value_changed("payment_mode"):
			draft_invoices = frappe.get_all(
				"Invoice", filters={"docstatus": 0, "team": self.name}, pluck="name"
			)

			for invoice in draft_invoices:
				frappe.db.set_value("Invoice", invoice, "payment_mode", self.payment_mode)

	def validate_payment_mode(self):
		if not self.payment_mode and self.get_balance() > 0:
			self.payment_mode = "Prepaid Credits"

		if self.has_value_changed("payment_mode"):
			if self.payment_mode == "Card":
				if frappe.db.count("Stripe Payment Method", {"org": self.name}) == 0:
					frappe.throw("No card added")
			if self.payment_mode == "Prepaid Credits":
				if self.get_balance() <= 0:
					frappe.throw("Account does not have sufficient balance")

		if not self.is_new() and not self.default_payment_method:
			# if default payment method is unset
			# then set the is_default field for Stripe Payment Method to 0
			payment_methods = frappe.db.get_list(
				"Stripe Payment Method", {"org": self.name, "is_default": 1}
			)
			for pm in payment_methods:
				doc = frappe.get_doc("Stripe Payment Method", pm.name)
				doc.is_default = 0
				doc.save()

	def update_billing_details(self, billing_details):
		if self.billing_address:
			address_doc = frappe.get_doc("Address", self.billing_address)
		else:
			address_doc = frappe.new_doc("Address")
			address_doc.address_title = billing_details.billing_name or self.billing_name
			address_doc.append(
				"links",
				{"link_doctype": self.doctype, "link_name": self.name, "link_title": self.name},
			)

		address_doc.update(
			{
				"address_line1": billing_details.address,
				"city": billing_details.city,
				"state": billing_details.state,
				"pincode": billing_details.postal_code,
				"country": billing_details.country,
				"gstin": billing_details.gstin,
			}
		)
		address_doc.save()
		address_doc.reload()

		self.billing_name = billing_details.billing_name or self.billing_name
		self.billing_address = address_doc.name
		self.save()
		self.reload()

		self.update_billing_details_on_stripe(address_doc)
		self.update_billing_details_on_frappeio()
		self.update_billing_details_on_draft_invoices()

	def update_billing_details_on_draft_invoices(self):
		draft_invoices = frappe.get_all(
			"Invoice", {"team": self.name, "docstatus": 0}, pluck="name"
		)
		for draft_invoice in draft_invoices:
			# Invoice.customer_name set by Invoice.validate()
			frappe.get_doc("Invoice", draft_invoice).save()

	def update_billing_details_on_frappeio(self):
		try:
			frappeio_client = get_frappe_io_connection()
		except FrappeioServerNotSet as e:
			if frappe.conf.developer_mode or frappe.flags.in_install or frappe.flags.in_test:
				return
			else:
				raise e

		previous_version = self.get_doc_before_save()

		if not previous_version:
			self.load_doc_before_save()
			previous_version = self.get_doc_before_save()

		previous_billing_name = previous_version.billing_name

		if previous_billing_name:
			try:
				frappeio_client.rename_doc("Customer", previous_billing_name, self.billing_name)
				frappe.msgprint(
					f"Renamed customer from {previous_billing_name} to {self.billing_name}"
				)
			except Exception:
				log_error(
					"Failed to rename customer on frappe.io", traceback=frappe.get_traceback()
				)

	def update_billing_details_on_stripe(self, address=None):
		stripe = get_stripe()
		if not address:
			address = frappe.get_doc("Address", self.billing_address)

		country_code = frappe.db.get_value("Country", address.country, "code")
		stripe.Customer.modify(
			self.stripe_customer_id,
			address={
				"line1": address.address_line1,
				"postal_code": address.pincode,
				"city": address.city,
				"state": address.state,
				"country": country_code.upper(),
			},
		)

	def set_org_currency(self):
		if not self.currency and self.country:
			self.currency = "INR" if self.country == "India" else "USD"

	def set_billing_name(self):
		if not self.billing_name:
			self.billing_name = frappe.utils.get_fullname(self.name)

	def set_partner_email(self):
		if self.erpnext_partner and not self.partner_email:
			self.partner_email = self.name

	@frappe.whitelist()
	def get_balance(self):
		res = frappe.db.get_all(
			"Balance Transaction",
			filters={"org": self.name, "docstatus": 1},
			order_by="creation desc",
			limit=1,
			pluck="ending_balance",
		)
		if not res:
			return 0
		return res[0]

	def get_onboarding(self):
		if self.payment_mode == "Partner Credits":
			billing_setup = True
		else:
			billing_setup = bool(
				self.payment_mode in ["Card", "Prepaid Credits"]
				and (self.default_payment_method or self.get_balance() > 0)
				and self.billing_address
			)

		site_created = frappe.db.count("Site", {"team": self.name}) > 0

		if self.via_erpnext:
			erpnext_domain = frappe.db.get_single_value("Press Settings", "erpnext_domain")
			erpnext_site = frappe.db.get_value(
				"Site",
				{"domain": erpnext_domain, "team": self.name, "status": ("!=", "Archived")},
				["name", "plan"],
				as_dict=1,
			)

			if erpnext_site is None:
				# Case: They have archived their ERPNext trial site
				# and created a frappe.cloud site now
				erpnext_site_plan_set = True
			else:
				erpnext_site_plan_set = erpnext_site.plan != "ERPNext Trial"
		else:
			erpnext_site = None
			erpnext_site_plan_set = True

		return {
			"account_created": True,
			"billing_setup": billing_setup,
			"erpnext_site": erpnext_site,
			"erpnext_site_plan_set": erpnext_site_plan_set,
			"site_created": site_created,
			"complete": billing_setup and site_created and erpnext_site_plan_set,
		}


def get_org_members(org):
	if not frappe.db.exists("Org", org):
		return []

	r = frappe.db.get_all("Org Member", filters={"parent": org}, fields=["user"])
	member_emails = [d.user for d in r]

	users = []
	if member_emails:
		users = frappe.db.sql(
			"""
				select u.name, u.first_name, u.last_name, GROUP_CONCAT(r.`role`) as roles
				from `tabUser` u
				left join `tabHas Role` r
				on (r.parent = u.name)
				where ifnull(u.name, '') in %s
				group by u.name
			""",
			[member_emails],
			as_dict=True,
		)
		for user in users:
			user.roles = (user.roles or "").split(",")

	return users
