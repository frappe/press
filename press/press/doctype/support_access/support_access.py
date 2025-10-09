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
		all_access: DF.Check
		allowed_for: DF.Literal["3", "6", "12", "24"]
		bench_ssh_access: DF.Check
		dashboard_access: DF.Check
		reason: DF.SmallText | None
		requested_by: DF.Link | None
		requested_team: DF.Link | None
		resources: DF.Table[SupportAccessResource]
		site_access: DF.Check
		status: DF.Literal["Pending", "Accepted", "Rejected"]
		target_team: DF.Link | None
	# end: auto-generated types

	dashboard_fields = (
		"requested_by",
		"requested_team",
		"target_team",
		"status",
		"allowed_for",
		"access_allowed_till",
	)

	def get_list_query(query, filters: dict | None, **args):
		filters = filters or {}
		team = get_current_team()
		Access = frappe.qb.DocType("Support Access")
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
