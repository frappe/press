# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class PartnerCertificate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		certificate_link: DF.Data | None
		course: DF.Data | None
		evaluator: DF.Data | None
		evaluator_name: DF.Data | None
		free: DF.Check
		issue_date: DF.Date | None
		partner_member_email: DF.Data | None
		partner_member_name: DF.Data | None
		team: DF.Link | None
		template: DF.Data | None
		version: DF.Data | None
	# end: auto-generated types

	dashboard_fields = (
		"certificate_link",
		"course",
		"version",
		"issue_date",
		"partner_member_name",
		"partner_member_email",
		"free",
		"team",
	)

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		PartnerCertificate = frappe.qb.DocType("Partner Certificate")
		Team = frappe.qb.DocType("Team")

		query = (
			frappe.qb.from_(PartnerCertificate)
			.inner_join(Team)
			.on(PartnerCertificate.team == Team.name)
			.select(
				PartnerCertificate.course,
				PartnerCertificate.version,
				PartnerCertificate.issue_date,
				PartnerCertificate.partner_member_name,
				PartnerCertificate.partner_member_email,
				PartnerCertificate.free,
				PartnerCertificate.certificate_link,
				Team.company_name.as_("team"),
			)
		)
		if filters:
			if filters.get("team"):
				query = query.where(PartnerCertificate.team == filters.get("team"))
			if filters.get("course"):
				query = query.where(PartnerCertificate.course == filters.get("course"))
			if filters.get("search-text"):
				search_text = f"%{filters.get('search-text')}%"
				query = query.where(
					(PartnerCertificate.partner_member_name.like(search_text))
					| (PartnerCertificate.partner_member_email.like(search_text))
					| (Team.company_name.like(search_text))
				)
		return query.run(as_dict=True)
