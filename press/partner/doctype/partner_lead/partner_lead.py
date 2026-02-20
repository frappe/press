# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class PartnerLead(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.partner.doctype.lead_followup.lead_followup import LeadFollowup

		additional_comments: DF.SmallText | None
		assistance_type: DF.Literal["Pre-sales Demo", "Plan suggestion", "Proposal", "Closing a deal"]
		company_name: DF.Data | None
		contact_no: DF.Data | None
		conversion_date: DF.Date | None
		country: DF.Link | None
		crm_deal: DF.Data | None
		deal_assistance_rating: DF.Rating
		domain: DF.Literal[
			"",
			"Distribution",
			"Manufacturing",
			"Retail",
			"Education",
			"Agriculture",
			"Healthcare",
			"Services",
			"Non Profit",
			"Other",
		]
		email: DF.Data | None
		employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		engagement_stage: DF.Literal[
			"",
			"Demo",
			"Qualification",
			"Learning",
			"Follow-up",
			"Quotation",
			"Negotiation",
			"Ready for Closing",
		]
		erpnext_success_pack_interested_in: DF.Data | None
		estimated_closure_date: DF.Date | None
		feedback_for_frappe: DF.SmallText | None
		feedback_to_partner: DF.SmallText | None
		followup: DF.Table[LeadFollowup]
		full_name: DF.Data | None
		hosting: DF.Literal["Frappe Cloud", "Self Hosted"]
		lead_name: DF.Data | None
		lead_rating: DF.Rating
		lead_source: DF.Literal["", "Partner Owned", "Passed to Partner", "Partner Listing"]
		lead_type: DF.Link | None
		lost_reason: DF.Literal[
			"Lost to Competitor",
			"No Response",
			"Budget Constraints",
			"Partner Rejected",
			"Trash Lead",
			"Free User",
			"Not Interested Anymore",
			"Other",
		]
		lost_reason_specify: DF.SmallText | None
		need_demo_before_implementation: DF.Check
		next_action_date: DF.Date | None
		organization_name: DF.Data | None
		origin: DF.Link | None
		partner_email: DF.Data | None
		partner_manager: DF.Data | None
		partner_team: DF.Link | None
		partner_territory: DF.Data | None
		passed_date: DF.Date | None
		plan_proposed: DF.Data | None
		probability: DF.Literal["Hot", "Cold", "Warm"]
		require_deal_assistance: DF.Check
		requirement: DF.Text | None
		requirements: DF.SmallText | None
		server_name: DF.Data | None
		site_url: DF.Data | None
		state: DF.Data | None
		status: DF.Literal["Open", "In Process", "Won", "Lost", "Junk", "Pass to Other Partner"]
		team_name: DF.Data | None
		territory: DF.Data | None
	# end: auto-generated types

	dashboard_fields = (
		"name",
		"organization_name",
		"state",
		"status",
		"engagement_stage",
		"lead_type",
		"lead_source",
		"lead_name",
		"domain",
		"conversion_date",
		"full_name",
		"email",
		"contact_no",
		"country",
		"plan_proposed",
		"site_url",
		"hosting",
		"estimated_closure_date",
		"probability",
		"requirement",
		"partner_team",
		"discussion",
		"lost_reason",
		"lost_reason_specify",
		"company_name",
	)

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		PartnerLead = frappe.qb.DocType("Partner Lead")
		query = (
			frappe.qb.from_(PartnerLead)
			.select(
				PartnerLead.name,
				PartnerLead.organization_name,
				PartnerLead.status,
				PartnerLead.engagement_stage,
				PartnerLead.lead_source,
				PartnerLead.lead_name,
				PartnerLead.company_name,
			)
			.limit(list_args["limit"])
			.offset(list_args["start"])
		)

		if filters:
			if filters.get("source"):
				query = query.where(PartnerLead.lead_source == filters.get("source"))
			if filters.get("status"):
				query = query.where(PartnerLead.status == filters.get("status"))
			if filters.get("origin"):
				query = query.where(PartnerLead.origin == filters.get("origin"))
			if filters.get("search-text"):
				search_text = f"%{filters.get('search-text')}%"
				query = query.where(
					(PartnerLead.organization_name.like(search_text))
					| (PartnerLead.lead_name.like(search_text))
					| (PartnerLead.company_name.like(search_text))
				)

		return query.run(as_dict=True)
