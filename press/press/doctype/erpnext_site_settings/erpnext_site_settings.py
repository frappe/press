# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class ERPNextSiteSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		emails: DF.Int
		expiry: DF.Date
		plan: DF.Data | None
		site: DF.Link
		space: DF.Int
		support_expiry: DF.Date | None
		users: DF.Int
	# end: auto-generated types

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
