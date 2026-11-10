# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import format_datetime, get_url, now_datetime

from press.utils import get_current_team

LINK_VALIDITY = timedelta(hours=48)

DOCUMENT_LABELS = {"Site": "site", "Release Group": "bench", "Server": "server"}
CONFIRM_METHODS = {
	"Site": "press.api.site.confirm_site_transfer",
	"Release Group": "press.api.bench.confirm_bench_transfer",
	"Server": "press.api.server.confirm_server_transfer",
}
DASHBOARD_ROUTES = {"Site": "sites", "Release Group": "groups", "Server": "servers"}


class TeamChange(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.team_change_resource.team_change_resource import TeamChangeResource

		balance_moved: DF.Float
		document_name: DF.DynamicLink | None
		document_type: DF.Link | None
		exchange_rate: DF.Float
		expires_on: DF.Datetime | None
		from_team: DF.Link
		key: DF.Data | None
		move_balance: DF.Check
		reason: DF.LongText | None
		resources: DF.Table[TeamChangeResource]
		to_team: DF.Link
		transfer_completed: DF.Check
		transfer_type: DF.Literal["Specific Resources", "Full Account"]
		transferred_by: DF.Link | None
		transferred_on: DF.Datetime | None
	# end: auto-generated types

	@property
	def is_dashboard_request(self) -> bool:
		"""A customer's request for one document, accepted from the emailed link. Else a desk transfer."""
		return bool(self.document_name)

	@property
	def label(self) -> str:
		doctype = self.document_type or ""
		return DOCUMENT_LABELS.get(doctype, doctype)

	@property
	def is_expired(self) -> bool:
		# Requests made before expiry existed have no date and stay valid
		return bool(self.expires_on) and now_datetime() > frappe.utils.get_datetime(self.expires_on)

	@property
	def is_being_accepted(self) -> bool:
		return bool(self.transfer_completed) and self.has_value_changed("transfer_completed")

	def before_insert(self):
		if not self.is_dashboard_request:
			return
		self.validate_no_pending_request()
		self.key = self.key or frappe.generate_hash("Team Change", 20)
		self.expires_on = now_datetime() + LINK_VALIDITY

	def validate(self):
		self.validate_not_completed_before()
		if self.from_team == self.to_team:
			frappe.throw(
				"The source team and the target team are the same. "
				"Pick the team that should receive the resources as the Target Team."
			)
		if self.is_dashboard_request:
			self.validate_dashboard_request()
		else:
			self.admin_transfer.validate()

	def validate_not_completed_before(self):
		before = self.get_doc_before_save()
		if before and before.transfer_completed:
			frappe.throw(
				"This transfer is already complete and can't be changed. "
				"Create a new Team Change to move more resources."
			)

	def validate_dashboard_request(self):
		self.validate_owner()
		if self.is_new() or self.is_being_accepted:
			self.validate_document_can_move()
		if self.is_being_accepted:
			self.validate_acceptance()

	def on_update(self):
		if not self.is_being_accepted:
			return
		if self.is_dashboard_request:
			self.move_requested_document()
		else:
			self.admin_transfer.move()

	@frappe.whitelist()
	def fetch_resources(self):
		self.validate_desk_transfer()
		self.admin_transfer.fetch_resources()

	@frappe.whitelist()
	def transfer(self):
		self.validate_desk_transfer()
		self.admin_transfer.transfer()

	def validate_desk_transfer(self):
		frappe.only_for(["System Manager", "Press Support", "Press Support Engineer"])
		if self.is_dashboard_request:
			frappe.throw(
				"This is a dashboard request, which the receiving team accepts from the emailed link. "
				"Create a new Team Change with the resources as rows to move them yourself."
			)

	@property
	def admin_transfer(self):
		from press.press.doctype.team_change.admin_transfer import AdminTransfer

		return AdminTransfer(self)

	def move_requested_document(self):
		if self.document_type == "Site":
			transfer_site(self.document_name, self.to_team)
		elif self.document_type == "Release Group":
			transfer_release_group(self.document_name, self.to_team)
		elif self.document_type == "Server":
			self.server_transfer.transfer(self.to_team)

	@property
	def server_transfer(self):
		from press.press.doctype.team_change.server_transfer import ServerTransfer

		return ServerTransfer(self.document_name, self.from_team)

	def validate_owner(self):
		team = frappe.db.get_value(self.document_type, self.document_name, "team")
		if team != self.from_team:
			frappe.throw(f"The owner of {self.document_type} is not {self.from_team}")

	def validate_no_pending_request(self):
		pending = frappe.db.get_value(
			"Team Change",
			{
				"document_type": self.document_type,
				"document_name": self.document_name,
				"transfer_completed": 0,
				"expires_on": (">", now_datetime()),
			},
			["to_team", "expires_on"],
			as_dict=True,
		)
		if pending:
			to_email = frappe.db.get_value("Team", pending.to_team, "user")
			frappe.throw(
				f"A transfer request for this {self.label} was already sent to {to_email}. "
				f"You can send a new request after {format_datetime(pending.expires_on, 'd MMM yyyy, h:mm a')}."
			)

	def validate_document_can_move(self):
		if self.document_type != "Server":
			return
		if blockers := self.server_transfer.blockers(self.to_team):
			frappe.throw(
				"This server can't be transferred yet:<br><br>" + "<br>".join(f"• {b}" for b in blockers),
				title="Transfer Not Possible",
			)

	def validate_acceptance(self):
		if self.is_expired:
			frappe.throw(
				f"This link has expired. Please ask the sender to send a new {self.label} transfer request."
			)
		for team in (self.from_team, self.to_team):
			validate_team_enabled(team)

	def send_confirmation_email(self, title: str):
		to_email = frappe.db.get_value("Team", self.to_team, "user")
		extra_args = (
			self.server_transfer.email_details(self.to_team) if self.document_type == "Server" else {}
		)
		link = get_url(f"/api/method/{CONFIRM_METHODS[self.document_type or '']}?key={self.key}")
		if frappe.conf.developer_mode:
			print(f"\n{self.label.capitalize()} transfer link for {to_email}\n{link}\n")

		frappe.sendmail(
			recipients=to_email,
			subject=f"Transfer {self.label.capitalize()} Ownership Confirmation",
			template="transfer_team_confirmation",
			args={
				"name": title,
				"type": self.label,
				"old_team": frappe.db.get_value("Team", self.from_team, "user"),
				"new_team": to_email,
				"transfer_url": link,
				"expires_on": format_datetime(self.expires_on, "d MMM yyyy, h:mm a"),
				**extra_args,
			},
		)


def validate_team_enabled(team: str):
	if not frappe.db.get_value("Team", team, "enabled"):
		frappe.throw(
			f"The team {team} is disabled, so this transfer can't be completed. "
			"Please make sure the team is enabled, then try again."
		)


def request_transfer(doc: Document, team_mail_id: str, reason: str | None, title: str) -> TeamChange:
	"""Create a Team Change for `doc` and email the confirmation link to the receiving team."""
	label = DOCUMENT_LABELS[doc.doctype]
	if doc.team != get_current_team():
		frappe.throw(
			f"Only a member of the team that owns this {label} can transfer it. "
			"Please switch to the owning team and try again."
		)

	to_team = frappe.db.get_value("Team", {"user": team_mail_id, "enabled": 1})
	if not to_team:
		frappe.throw(
			"We couldn't find an active team with that email. Please check the address and make sure "
			"the recipient has an active Frappe Cloud account."
		)
	if to_team == doc.team:
		frappe.throw(f"This {label} is already owned by the team {team_mail_id}.")

	team_change: TeamChange = frappe.get_doc(
		{
			"doctype": "Team Change",
			"document_type": doc.doctype,
			"document_name": doc.name,
			"from_team": doc.team,
			"to_team": to_team,
			"reason": reason or "",
		}
	).insert(ignore_permissions=True)  # Team Change is System Manager only; ownership is checked above
	team_change.send_confirmation_email(title)
	return team_change


def confirm_transfer(key: str, document_type: str):
	"""Accept the transfer behind `key`. Used by the links in the confirmation emails."""
	label = DOCUMENT_LABELS[document_type]
	if frappe.session.user == "Guest":
		return _not_permitted(f"You need to be logged in to confirm the {label} transfer.", show_login=True)

	name = isinstance(key, str) and frappe.db.get_value(
		"Team Change", {"key": key, "document_type": document_type}
	)
	if not name:
		return _not_permitted("The link you are using is invalid or expired.")

	team_change = TeamChange("Team Change", name)
	if error := _link_error(team_change):
		return _not_permitted(error)

	try:
		team_change.transfer_completed = True
		# Team Change is System Manager only; the key and team membership are checked above
		team_change.save(ignore_permissions=True)
	except frappe.ValidationError as e:
		frappe.db.rollback()
		return _not_permitted(str(e), title=_("Transfer Not Completed"))
	frappe.db.commit()

	frappe.response.type = "redirect"
	frappe.response.location = f"/dashboard/{DASHBOARD_ROUTES[document_type]}/{team_change.document_name}"
	return None


def _link_error(team_change: TeamChange) -> str | None:
	if team_change.transfer_completed:
		return "This link has already been used."
	if team_change.is_expired:
		return f"This link has expired. Please ask the sender to send a new {team_change.label} transfer request."
	if not frappe.db.exists(
		"Team Member", {"user": frappe.session.user, "parent": team_change.to_team, "parenttype": "Team"}
	):
		return f"You are not a member of the team to which the {team_change.label} is being transferred."
	return None


def _not_permitted(message: str, title: str | None = None, show_login: bool = False):
	return frappe.respond_as_web_page(
		title or _("Not Permitted"),
		_(message),
		http_status_code=403,
		indicator_color="red",
		primary_action="/dashboard/login" if show_login else None,
		primary_label=_("Login") if show_login else None,
	)


def transfer_site(site: str, to_team: str):
	frappe.db.set_value("Site", site, "team", to_team)
	frappe.db.set_value("Subscription", {"document_name": site}, "team", to_team)

	frappe.db.set_value("Site Domain", {"site": site}, "team", to_team)
	tls_certificates = frappe.get_all("Site Domain", filters={"site": site}, pluck="tls_certificate")
	frappe.db.set_value("TLS Certificate", {"name": ["in", tls_certificates]}, "team", to_team)

	frappe.db.set_value("Site Backup", {"site": site}, "team", to_team)
	frappe.db.set_value("Site Database User", {"site": site}, "team", to_team)
	frappe.db.delete("Press Role Permission", {"site": site})


def transfer_release_group(group: str, to_team: str):
	frappe.db.set_value("Release Group", group, "team", to_team)
	# Bench.team is fetched from the group only on insert, and the Bench permission query reads it
	frappe.db.set_value("Bench", {"group": group}, "team", to_team)
	frappe.db.delete("Press Role Permission", {"release_group": group})
	# Skip onboarding for receiving team so they can access bench groups immediately
	# Actual resource usage (servers/sites) will still require billing setup
	frappe.db.set_value("Team", to_team, "skip_onboarding", 1)
