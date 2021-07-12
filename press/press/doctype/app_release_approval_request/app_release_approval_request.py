# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document
from frappe.model.naming import make_autoname
from press.press.doctype.app_release.app_release import AppRelease


class AppReleaseApprovalRequest(Document):
	def autoname(self):
		app = self.marketplace_app
		series = f"REQ-{app}-.#####"
		self.name = make_autoname(series)

	def validate(self):
		self.update_release_status()

	@classmethod
	def create(cls, marketplace_app: str, app_release: str):
		request: cls = frappe.new_doc("App Release Approval Request")
		request.marketplace_app = marketplace_app
		request.app_release = app_release
		request.save(ignore_permissions=True)

	def update_release_status(self):
		release: AppRelease = frappe.get_doc("App Release", self.app_release)
		release.status = "Awaiting Approval"
		release.save(ignore_permissions=True)
