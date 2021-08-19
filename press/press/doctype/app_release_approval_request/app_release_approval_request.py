# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document
from frappe.model.naming import make_autoname
from press.press.doctype.app_release.app_release import AppRelease
from press.press.doctype.marketplace_app.marketplace_app import MarketplaceApp


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

	def before_insert(self):
		self.request_already_exists()
		self.another_request_awaiting_approval()
		self.update_release_status()

	def request_already_exists(self):
		requests = frappe.get_all(
			"App Release Approval Request",
			filters={"app_release": self.app_release, "status": ("!=", "Cancelled")},
		)

		if len(requests) > 0:
			frappe.throw("An active request for this app release already exists!")

	def another_request_awaiting_approval(self):
		requests = frappe.get_all(
			"App Release Approval Request",
			filters={"marketplace_app": self.marketplace_app, "status": "Open"},
		)

		if len(requests) > 0:
			frappe.throw("A previous release is already awaiting approval!")

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
			self.notify_publisher()
		elif status_updated and self.status == "Approved":
			release.status = "Approved"
			self.notify_publisher()
		elif status_updated and self.status == "Cancelled":
			release.status = "Draft"

		release.save(ignore_permissions=True)
		frappe.db.commit()

		if status_updated:
			self.publish_status_change(release.source)

	def publish_status_change(self, source):
		frappe.publish_realtime(event="request_status_changed", message={"source": source})

	def notify_publisher(self):
		marketplace_app: MarketplaceApp = frappe.get_doc(
			"Marketplace App", self.marketplace_app
		)
		app_release: AppRelease = frappe.get_doc("App Release", self.app_release)
		publisher_email = marketplace_app.team

		frappe.sendmail(
			[publisher_email],
			subject=f"Frappe Cloud Marketplace: {marketplace_app.title}",
			args={
				"subject": "Update on your app release publish request",
				"status": self.status,
				"rejection_reason": self.reason_for_rejection,
				"commit_message": app_release.message,
				"releases_link": f"{frappe.local.site}/dashboard/developer/apps/{self.marketplace_app}/releases",
			},
			template="app_approval_request_update",
		)
