# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Count

from press.utils import get_current_team


class PartnerAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		audit_date: DF.Date | None
		audit_report: DF.Attach | None
		conducted_by: DF.Link | None
		implementation_finding: DF.TextEditor | None
		implementation_observation: DF.TextEditor | None
		implementation_summary: DF.TextEditor | None
		mode_of_audit: DF.Literal["", "Online", "In-Person", "Hybrid"]
		next_actions: DF.TextEditor | None
		partner_team: DF.Link | None
		partner_tier: DF.Data | None
		proposed_audit_date: DF.Date | None
		requested_on: DF.Date | None
		sales_finding: DF.TextEditor | None
		sales_observation: DF.TextEditor | None
		sales_summary: DF.TextEditor | None
		status: DF.Literal["Requested", "Scheduled", "In Progress", "Completed", "On Hold", "Cancelled"]
		support_finding: DF.TextEditor | None
		support_observation: DF.TextEditor | None
		support_summary: DF.TextEditor | None
	# end: auto-generated types

	dashboard_fields = (
		"partner_team",
		"partner_tier",
		"mode_of_audit",
		"status",
		"audit_date",
		"conducted_by",
		"proposed_audit_date",
	)

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		PartnerAudit = frappe.qb.DocType("Partner Audit")
		Team = frappe.qb.DocType("Team")
		NonConformance = frappe.qb.DocType("Partner Non Conformance")

		query = (
			frappe.qb.from_(PartnerAudit)
			.left_join(NonConformance)
			.on(NonConformance.partner_audit == PartnerAudit.name)
			.inner_join(Team)
			.on(PartnerAudit.partner_team == Team.name)
			.select(
				Team.company_name.as_("partner_team"),
				PartnerAudit.mode_of_audit,
				PartnerAudit.status,
				PartnerAudit.audit_date,
				PartnerAudit.conducted_by,
				PartnerAudit.proposed_audit_date,
				PartnerAudit.name,
				Count(NonConformance.name).as_("non_conformance_count"),
			)
			.groupby(PartnerAudit.name)
			.limit(list_args["limit"])
			.offset(list_args["start"])
			.orderby(PartnerAudit.modified, order=frappe.qb.desc)
		)

		# This query is built from scratch, so the scoping `press.api.client`
		# applied to the query it handed over is gone. Reapply it. A partner
		# picking their own team in `filters` is redundant but harmless.
		if not frappe.local.system_user():
			query = query.where(PartnerAudit.partner_team == get_current_team())
		elif filters.get("team"):
			query = query.where(PartnerAudit.partner_team == filters["team"])
		if filters.get("status") and filters["status"] != "All":
			query = query.where(PartnerAudit.status == filters["status"])
		if filters.get("mode_of_audit") and filters["mode_of_audit"] != "All":
			query = query.where(PartnerAudit.mode_of_audit == filters["mode_of_audit"])
		if filters.get("proposed_audit_date"):
			query = query.where(PartnerAudit.proposed_audit_date == filters["proposed_audit_date"])

		return query.run(as_dict=True)
