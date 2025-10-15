# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.query_builder import Criterion

from press.utils import get_current_team


class SupportAccess(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.support_access_resource.support_access_resource import SupportAccessResource

		access_allowed_till: DF.Datetime | None
		allowed_for: DF.Literal["3", "6", "12", "24"]
		login_as_administrator: DF.Check
		reason: DF.SmallText | None
		requested_by: DF.Link | None
		requested_team: DF.Link | None
		resources: DF.Table[SupportAccessResource]
		site_domains: DF.Check
		status: DF.Literal["Pending", "Accepted", "Rejected"]
		target_team: DF.Link | None
	# end: auto-generated types

	dashboard_fields = (
		"access_allowed_till",
		"allowed_for",
		"login_as_administrator",
		"reason",
		"requested_by",
		"requested_team",
		"site_domains",
		"status",
		"target_team",
	)

	def get_list_query(query, filters: dict | None, **args):
		filters = filters or {}
		team = get_current_team()
		Access = frappe.qb.DocType("Support Access")
		AccessResource = frappe.qb.DocType("Support Access Resource")
		query = (
			query.join(AccessResource)
			.on(AccessResource.parent == Access.name)
			.select(AccessResource.document_type.as_("resource_type"))
			.select(AccessResource.document_name.as_("resource_name"))
		)
		conditions = []
		match filters.get("source"):
			case "Received":
				conditions.append(Access.target_team == team)
			case "Sent":
				conditions.append(Access.requested_by == frappe.session.user)
				conditions.append(Access.requested_team == team)
		return query.where(Criterion.any(conditions)).run(as_dict=True)

	@property
	def access_expired(self):
		return bool(
			self.access_allowed_till
			and frappe.utils.get_datetime(self.access_allowed_till) < frappe.utils.now_datetime()
		)

	def before_validate(self):
		self.requested_by = self.requested_by or frappe.session.user
		self.requested_team = self.requested_team or get_current_team()
		self.set_expiry()

	def set_expiry(self):
		doc_before = self.get_doc_before_save()
		hours = frappe.utils.cint(self.allowed_for)
		if hours and doc_before and doc_before.status != self.status and self.status == "Accepted":
			self.access_allowed_till = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=hours)

	def validate(self):
		self.validate_status_change()
		self.validate_expiry()
		self.validate_target_team()

	def validate_status_change(self):
		team = get_current_team()
		doc_before = self.get_doc_before_save()
		status_changed = doc_before and doc_before.status != self.status
		if status_changed and self.target_team != team:
			frappe.throw("Only the target team can change the status")
		if status_changed and doc_before.status != "Pending":
			frappe.throw("Status can only be changed if it is Pending")

	def validate_expiry(self):
		if self.access_expired:
			frappe.throw("Access expiry must be in the future")
		if self.status != "Accepted" and self.access_allowed_till:
			frappe.throw("Access expiry can only be set if request is accepted")

	def validate_target_team(self):
		teams = set()
		for resource in self.resources:
			team = frappe.get_value(resource.document_type, resource.document_name, "team")
			teams.add(team)
		if len(teams) != 1:
			frappe.throw("Resources must belong to the same team")
		self.target_team = teams.pop()

	def after_insert(self):
		self.notify_on_request()

	def on_update(self):
		doc_before = self.get_doc_before_save()
		if doc_before and doc_before.status != self.status:
			self.notify_on_status_change()

	def notify_on_status_change(self):
		title = f"Access Request {self.status}"
		message = f"Your request for support access has been {self.status.lower()}."

		frappe.get_doc(
			{
				"doctype": "Press Notification",
				"team": self.requested_team,
				"type": "Support Access",
				"document_type": "Support Access",
				"document_name": self.name,
				"title": title,
				"message": message,
			}
		).insert()

		frappe.publish_realtime(
			"press_notification",
			doctype="Press Notification",
			message={
				"team": self.requested_team,
			},
		)

	def notify_on_request(self):
		title = "New Access Request"
		message = f"{self.requested_by} has requested support access for one of your resources."

		frappe.get_doc(
			{
				"doctype": "Press Notification",
				"team": self.target_team,
				"type": "Support Access",
				"document_type": "Support Access",
				"document_name": self.name,
				"title": title,
				"message": message,
			}
		).insert()

		frappe.publish_realtime(
			"press_notification",
			doctype="Press Notification",
			message={
				"team": self.target_team,
			},
		)
