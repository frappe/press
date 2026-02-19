# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


import frappe
import frappe.utils
from frappe import _
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
		allowed_for: DF.Literal["3", "6", "12", "24", "72", "168"]
		bench_ssh: DF.Check
		login_as_administrator: DF.Check
		reason: DF.SmallText | None
		requested_by: DF.Link | None
		requested_team: DF.Link | None
		resources: DF.Table[SupportAccessResource]
		site_domains: DF.Check
		site_release_group: DF.Check
		status: DF.Literal["Pending", "Accepted", "Rejected", "Forfeited", "Revoked"]
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
			.where(Access.requested_team == team | Access.target_team == team)
		)
		conditions = []
		match filters.get("source"):
			case "Received":
				conditions.append(Access.target_team == team)
			case "Sent":
				conditions.append(Access.requested_by == frappe.session.user)
				conditions.append(Access.requested_team == team)
		return query.where(Criterion.any(conditions)).run(as_dict=True)

	def has_permission(self, permtype="read", *, debug=False, user=None) -> bool:
		permission = super().has_permission(permtype, debug=debug, user=user)
		if permtype == "read":
			if permission and (get_current_team() in (self.requested_team, self.target_team)):
				return True
			return False
		return permission

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
		self.resolve_sites()
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

	def resolve_sites(self):
		for resource in self.resources:
			if resource.document_type == "Site":
				resource.document_name = self.resolve_site_name(resource.document_name)

	def resolve_site_name(self, site) -> str:
		try:
			domain = frappe.get_doc("Site Domain", site)
			return domain.site
		except frappe.DoesNotExistError:
			return site

	def validate(self):
		self.validate_status_change()
		self.validate_expiry()
		self.validate_target_team()

	@property
	def target_statuses(self) -> list[str]:
		"""
		Returns the possible target statuses for the current user.
		"""
		current_team = get_current_team()
		if self.target_team == current_team:
			return ["Accepted", "Rejected", "Revoked"]
		if self.requested_team == current_team:
			return ["Pending", "Forfeited"]
		return []

	def is_valid_status_transition(self, status_from: str, status_to: str) -> bool:
		"""
		Checks if status can be changed from `status_from` to `status_to`.
		"""
		return status_to in {
			"Pending": ["Accepted", "Rejected"],
			"Accepted": ["Revoked", "Forfeited"],
			"Rejected": [],
			"Forfeited": [],
			"Revoked": [],
		}.get(status_from, [])

	def validate_status_change(self):
		status_changed = self.has_value_changed("status")
		if not status_changed:
			return
		doc_before = self.get_doc_before_save()
		if not doc_before:
			return
		status_before = doc_before.status
		status_after = self.status
		if not self.is_valid_status_transition(status_before, status_after):
			frappe.throw(f"Cannot change status from {status_before} to {status_after}")
		if status_after not in self.target_statuses:
			frappe.throw("You are not allowed to set this status")

	def validate_expiry(self):
		if self.access_expired:
			frappe.throw("Access expiry must be in the future")
		if self.status == "Pending" and self.access_allowed_till:
			frappe.throw("Pending requests cannot have access expiry")

	def validate_target_team(self):
		teams = set()
		for resource in self.resources:
			team = frappe.get_value(resource.document_type, resource.document_name, "team")
			teams.add(team)
		if len(teams) != 1:
			frappe.throw("Resources must belong to the same team")
		self.target_team = teams.pop()

	def validate_validity_change(self):
		is_target_team = get_current_team() == self.target_team
		if self.has_value_changed("allowed_for") and not is_target_team:
			message = _("You are not allowed to change the validity period.")
			frappe.throw(message, frappe.ValidationError)
		if self.status != "Pending":
			message = _("Cannot change validity period of a processed request.")
			frappe.throw(message, frappe.ValidationError)

	def after_insert(self):
		self.notify_on_request()

	def on_update(self):
		self.notify_on_status_change()

	def notify_on_status_change(self):
		if not self.has_value_changed("status"):
			return

		title = f"Access Request {self.status}"
		message = f"Your request for support access has been {self.status.lower()}."
		recipient = self.requested_by

		if self.status == "Forfeited":
			message = "Support access has been forfieted."
			recipient = self.target_team

		frappe.sendmail(
			subject=title,
			message=message,
			recipients=recipient,
			template="access_request_update",
			args={
				"status": self.status,
				"resources": self.resources,
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
				"reason": self.reason,
				"resources": self.resources,
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
