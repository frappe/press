# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from shutil import ignore_patterns
import frappe

from frappe.model.document import Document
from frappe.model.naming import make_autoname
from press.press.doctype.app_release.app_release import AppRelease


class AppReleaseApprovalRequest(Document):
	@classmethod
	def create(cls, marketplace_app: str, app_release: str):
		"""Create a new `App Release Approval Request`"""
		request: cls = frappe.new_doc("App Release Approval Request")
		request.marketplace_app = marketplace_app
		request.app_release = app_release
		request.save(ignore_permissions=True)

	def autoname(self):
		app = self.marketplace_app
		series = f"REQ-{app}-.#####"
		self.name = make_autoname(series)

	def validate(self):
		self.update_release_status()

	def update_release_status(self):
		release: AppRelease = frappe.get_doc("App Release", self.app_release)
		release.status = "Awaiting Approval"
		release.save(ignore_permissions=True)

	def on_update(self):
		old_doc = self.get_doc_before_save()
		status_updated = old_doc.status != self.status

		release = frappe.get_doc("App Release", self.app_release)

		if status_updated and self.status == "Rejected":
			release.status = "Rejected"
			self.notifty_publisher()
		elif status_updated and self.status == "Approved":
			release.status = "Published"
			self.notifty_publisher()
		elif status_updated and self.status == "Cancelled":
			release.status = "Draft"

		release.save(ignore_permissions=True)

	def notifty_publisher(self):
		if self.status == "Rejected":
			print("Hey, your app was Rejected. Work hard!")
		elif self.status == "Approved":
			print("Congratz! Your app release was approved and is published now!")