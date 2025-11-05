# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.query_builder import Criterion, JoinType
from frappe.query_builder.functions import Count

from press.utils import get_current_team


class SupportAccess(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.support_access_resource.support_access_resource import SupportAccessResource

		access_allowed_till: DF.Datetime | None
		allowed_for: DF.Literal["3", "6", "12", "24", "72"]
		bench_ssh: DF.Check
		login_as_administrator: DF.Check
		reason: DF.SmallText | None
		requested_by: DF.Link | None
		requested_team: DF.Link | None
		resources: DF.Table[SupportAccessResource]
		site_domains: DF.Check
		site_release_group: DF.Check
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
		"resources",
		"site_domains",
		"site_release_group",
		"status",
		"target_team",
		"bench_ssh",
	)

	def get_list_query(query, filters: dict | None, **args):
		filters = filters or {}
		team = get_current_team()
		Access = frappe.qb.DocType("Support Access")
		AccessResource = frappe.qb.DocType("Support Access Resource")
		query = (
			query.join(AccessResource, JoinType.left)
			.on(AccessResource.parent == Access.name)
			.select(Count(AccessResource.name).as_("resource_count"))
			.groupby(Access.name)
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
		self.add_release_group()

	def add_release_group(self):
		"""
		Add release group and bench as resources if `site_release_group` is checked.
		"""

		if not self.site_release_group:
			return

		# Only add release group and bench for new requests. Meaning, do not
		# add them on updates.
		if not self.is_new():
			return

		site = None
		for resource in self.resources:
			if resource.document_type == "Site":
				site = resource.document_name
				break
		if not site:
			return

		site = frappe.get_doc("Site", site)
		release_group = frappe.get_doc("Release Group", site.group)

		# Ensure release group and site belong to the same team.
		if site.team != release_group.team:
			return

		# Add release group as a resource.
		self.append(
			"resources",
			{
				"document_type": "Release Group",
				"document_name": release_group.name,
			},
		)

		# Add bench as a resource.
		self.append(
			"resources",
			{
				"document_type": "Bench",
				"document_name": site.bench,
			},
		)

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

		frappe.sendmail(
			subject=title,
			message=message,
			recipients=self.requested_by,
			template="access_request_update",
			args={
				"status": self.status,
			},
		)

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
		team_email = frappe.get_value("Team", self.target_team, "user")

		frappe.sendmail(
			subject=title,
			message=message,
			recipients=team_email,
			template="access_request",
			args={
				"requested_by": self.requested_by,
				"reason": self.reason,
			},
		)

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
