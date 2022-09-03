# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class ERPNextSiteSettings(Document):
	def on_update(self):
		config_keys = ("users", "expiry", "emails", "space", "current_plan")
		values = (self.users, self.expiry, self.emails, self.space, self.plan)

		site = frappe.get_doc("Site", self.site)
		config = json.loads(site.config)
		limits = config.get("limits", {})

		limits.update(dict(zip(config_keys, values)))

		# remove null/empty values
		limits = {k: v for k, v in limits.items() if v}

		site.update_site_config({"limits": limits})
