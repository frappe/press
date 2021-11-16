# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe


from frappe.model.document import Document
from press.press.doctype.site.site import Site


class MarketplaceAppSubscription(Document):
	def validate(self):
		self.validate_plan()
		self.set_secret_key()

	def validate_plan(self):
		doctype_for_plan = frappe.db.get_value("Plan", self.plan, "document_type")

		if doctype_for_plan != "Marketplace App":
			frappe.throw(
				"Plan should be a Marketplace App document type plan, is"
				f" {doctype_for_plan} instead."
			)

	def set_secret_key(self):
		if not self.secret_key:
			from hashlib import blake2b

			h = blake2b(digest_size=20)
			h.update(self.name.encode())
			self.secret_key = h.hexdigest()

	def after_insert(self):
		#TODO: Check if this key already exists
		#TODO: Make the config value internal
		self.set_secret_key_in_site_config()

	def set_secret_key_in_site_config(self):
		site_doc: Site = frappe.get_doc("Site", self.site)
		
		key = f"sk_{self.app}"
		value = self.secret_key
		config = {key: value}

		site_doc.update_site_config(config)

	@frappe.whitelist()
	def activate(self):
		if self.status == "Active":
			frappe.throw("Subscription is already active.")
		
		self.status = "Active"
		self.save()