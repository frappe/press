# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class TeamChange(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		document_name: DF.DynamicLink
		document_type: DF.Link
		from_team: DF.Link
		key: DF.Data | None
		reason: DF.LongText | None
		to_team: DF.Link
		transfer_completed: DF.Check
	# end: auto-generated types

	def validate(self):
		team = frappe.get_doc(self.document_type, self.document_name).team
		if team != self.from_team:
			frappe.throw(f"The owner of {self.document_type} is not {self.from_team}")

	def on_update(self):
		if self.document_type == "Site" and self.transfer_completed:
			frappe.db.set_value("Site", self.document_name, "team", self.to_team)

			frappe.db.set_value(
				"Subscription",
				{"document_name": self.document_name},
				"team",
				self.to_team,
			)

			frappe.db.set_value("Site Domain", {"site": self.document_name}, "team", self.to_team)
			tls_certificates = frappe.get_all(
				"Site Domain",
				filters={"site": self.document_name},
				fields=["tls_certificate"],
				pluck="tls_certificate",
			)
			frappe.db.set_value("TLS Certificate", {"name": ["in", tls_certificates]}, "team", self.to_team)

			frappe.db.set_value("Site Backup", {"site": self.document_name}, "team", self.to_team)

			frappe.db.set_value("Site Database User", {"site": self.document_name}, "team", self.to_team)

<<<<<<< HEAD
		if self.document_type == "Release Group" and self.transfer_completed:
			frappe.db.set_value("Release Group", self.document_name, "team", self.to_team)
			# Skip onboarding for receiving team so they can access bench groups immediately
			# Actual resource usage (servers/sites) will still require billing setup
			frappe.db.set_value("Team", self.to_team, "skip_onboarding", 1)
=======
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
>>>>>>> f857347 (fix(team-change): Limit Team Change records to System Managers)
