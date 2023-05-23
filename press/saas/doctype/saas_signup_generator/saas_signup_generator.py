# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator
from press.utils import get_country_info


class SaasSignupGenerator(WebsiteGenerator):
	website = frappe._dict(
		template="templates/saas/signup.html",
		condition_field="publish",
		page_title_field="app_title",
	)

	def get_context(self, context):
		context.parents = [{"name": "Marketplace App"}]
		country_info = get_country_info() or {}
		country_name = country_info.get("country")
		context.country_name = (
			country_name if frappe.db.exists("Country", country_name) else ""
		)

		return context

	def validate(self):
		if not self.custom_route:
			self.route = f"{self.app.replace('_', '')}/signup"
