# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator


class SaasSetupAccountGenerator(WebsiteGenerator):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link | None
		app_title: DF.Data | None
		custom_route: DF.Check
		domain: DF.Data | None
		headless: DF.Check
		image_path: DF.Data | None
		publish: DF.Check
		route: DF.Data | None
	# end: auto-generated types

	website = frappe._dict(
		template="templates/saas/setup-account.html",
		condition_field="publish",
		page_title_field="app_title",
	)

	def get_context(self, context):
		context.parents = [{"name": "Marketplace App"}]

	def validate(self):
		if not self.custom_route:
			self.route = f"{self.app.replace('_', '')}/setup-account"
