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

		if self.document_type == "Release Group" and self.transfer_completed:
			frappe.db.set_value("Release Group", self.document_name, "team", self.to_team)
			# Skip onboarding for receiving team so they can access bench groups immediately
			# Actual resource usage (servers/sites) will still require billing setup
			frappe.db.set_value("Team", self.to_team, "skip_onboarding", 1)
