# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ERPNextSiteSettings(Document):
	def on_update(self):
		limits = {
			"users": self.users,
			"expiry": self.expiry,
			"emails": self.emails,
			"space": self.space,
			"current_plan": self.plan,
		}

		# remove null/empty values
		limits = {k: v for k, v in limits.items() if v}

		site = frappe.get_doc("Site", self.site)
		site.update_site_config({"limits": limits})
