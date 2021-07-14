# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document
from frappe.model.naming import make_autoname
from press.press.doctype.app_release.app_release import AppRelease


class AppReleaseApprovalRequest(Document):
	@staticmethod
	def create(marketplace_app: str, app_release: str):
		"""Create a new `App Release Approval Request`"""
		request = frappe.new_doc("App Release Approval Request")
		request.marketplace_app = marketplace_app
		request.app_release = app_release
		request.save(ignore_permissions=True)

	def cancel(self):
		self.status = "Cancelled"
		self.save(ignore_permissions=True)

	def autoname(self):
		app = self.marketplace_app
		series = f"REQ-{app}-.#####"
		self.name = make_autoname(series)

	def validate(self):
		self.update_release_status()

	def before_insert(self):
		self.request_already_exists()

	def request_already_exists(self):
		requests = frappe.get_all(
			"App Release Approval Request",
			filters={"app_release": self.app_release, "status": ("!=", "Cancelled")},
		)

		if len(requests) > 0:
			frappe.throw("An active request for this app release already exists!")

	def update_release_status(self):
		release: AppRelease = frappe.get_doc("App Release", self.app_release)
		release.status = "Awaiting Approval"
		release.save(ignore_permissions=True)

	def on_update(self):
		old_doc = self.get_doc_before_save()

		if old_doc is None:
			return

		status_updated = old_doc.status != self.status

		release = frappe.get_doc("App Release", self.app_release)

		if status_updated and self.status == "Rejected":
			release.status = "Rejected"
			self.notifty_publisher()
		elif status_updated and self.status == "Approved":
			release.status = "Approved"
			self.notifty_publisher()
		elif status_updated and self.status == "Cancelled":
			release.status = "Draft"

		release.save(ignore_permissions=True)

	def notifty_publisher(self):
		if self.status == "Rejected":
			print("Hey, your app was Rejected. Work hard!")
		elif self.status == "Approved":
			print("Congratz! Your app release was approved and is published now!")