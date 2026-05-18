# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class AppReleaseApprovalRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		app: DF.Link | None
		app_release: DF.Link
		marketplace_app: DF.Link
		reason_for_rejection: DF.TextEditor | None
		reviewed_by: DF.Link | None
		status: DF.Literal["Open", "Cancelled", "Approved", "Rejected"]
		team: DF.Link | None
	# end: auto-generated types

	dashboard_fields = [  # noqa: RUF012
		"name",
		"marketplace_app",
		"app_release",
		"status",
	]

	def before_save(self):
		apps = frappe.get_all("Featured App", {"parent": "Marketplace Settings"}, pluck="app")
		teams = frappe.get_all("Auto Release Team", {"parent": "Marketplace Settings"}, pluck="team")
		if self.team in teams or self.marketplace_app in apps:
			self.status = "Approved"

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
		# only validate if status is being being changed to Approved
		if self.status == "Approved":
			self.validate_audit_for_approval()

	def before_insert(self):
		self.request_already_exists()
		self.another_request_awaiting_approval()
		self.check_release_not_yanked()
		self.update_release_status()

	def request_already_exists(self):
		requests = frappe.get_all(
			"App Release Approval Request",
			filters={"app_release": self.app_release, "status": ("!=", "Cancelled")},
		)

		if len(requests) > 0:
			frappe.throw("An active request for this app release already exists!")

	def another_request_awaiting_approval(self):
		request_source = frappe.db.get_value("App Release", self.app_release, "source")

		releases_awaiting_approval = frappe.get_all(
			"App Release Approval Request",
			filters={"marketplace_app": self.marketplace_app, "status": "Open"},
			pluck="app_release",
		)
		sources_awaiting_approval = [
			frappe.db.get_value("App Release", r, "source") for r in releases_awaiting_approval
		]

		# A request for this source is already open
		if request_source in sources_awaiting_approval:
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

	def notify_publisher(self):
		marketplace_app = frappe.get_doc("Marketplace App", self.marketplace_app)
		app_release: AppRelease = frappe.get_doc("App Release", self.app_release)
		publisher_email = frappe.get_doc("Team", marketplace_app.team).user

		frappe.sendmail(
			[publisher_email],
			subject=f"Frappe Cloud Marketplace: {marketplace_app.title}",
			args={
				"subject": "Update on your app release publish request",
				"status": self.status,
				"rejection_reason": self.reason_for_rejection,
				"commit_message": app_release.message,
				"releases_link": f"{frappe.local.site}/dashboard/marketplace/apps/{self.marketplace_app}/releases",
			},
			template="app_approval_request_update",
		)

	def validate_audit_for_approval(self):
		bypass_automated_audit = frappe.db.get_value(
			"Marketplace App", self.marketplace_app, "bypass_automated_audit"
		)
		if bypass_automated_audit:
			return

		latest_audit = frappe.get_all(
			"Marketplace App Audit",
			filters={"app_release": self.app_release},
			fields=["name", "status", "audit_result", "audit_summary"],
			order_by="creation desc",
			limit=1,
		)
		if not latest_audit:
			frappe.throw(
				"Cannot approve: No audit found for this release. "
				"An audit must complete successfully before approval."
			)

		audit = latest_audit[0]
		if audit.status in ("Queued", "Running"):
			frappe.throw(
				f"Cannot approve: Audit {audit.name} is still {audit.status}. Please wait for it to complete."
			)

		if audit.status == "Failed":
			frappe.throw(
				f"Cannot approve: Audit {audit.name} failed. Please investigate and rerun the audit."
			)

		if audit.audit_result not in ["Pass", "Needs Improvement"]:
			frappe.throw(
				f"Cannot approve: Audit {audit.name} completed with result '{audit.audit_result}'. "
				f"Only 'Pass' or 'Needs Improvement' results allow approval.\n\n"
				f"Summary: {audit.audit_summary or 'N/A'}"
			)

	def check_release_not_yanked(self):
		"""
		Prevent approval requests for releases that failed audit and were yanked.
		"""
		release_status = frappe.db.get_value("App Release", self.app_release, "status")
		if release_status == "Yanked":
			frappe.throw(
				"Cannot create a approval request for a yanked release. This release was yanked due to audit failure. Please fix the issues and publish a new release."
			)
