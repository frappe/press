# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class PartnerLead(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.partner.doctype.lead_followup.lead_followup import LeadFollowup

		additional_comments: DF.SmallText | None
		company_name: DF.Data | None
		contact_no: DF.Data | None
		conversion_date: DF.Date | None
		country: DF.Link | None
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
		lead_source: DF.Literal["", "Partner Owned", "Passed to Partner", "Partner Listing", "Public Webinar"]
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
		lost_reason_specify: DF.Data | None
		need_demo_before_implementation: DF.Check
		next_action_date: DF.Date | None
		organization_name: DF.Data | None
		origin: DF.Link | None
		partner_email: DF.Data | None
		partner_manager: DF.Data | None
		partner_team: DF.Link | None
		partner_territory: DF.Data | None
		plan_proposed: DF.Data | None
		probability: DF.Literal["Hot", "Cold", "Warm"]
		requirement: DF.Text | None
		site_url: DF.Data | None
		state: DF.Data | None
		status: DF.Literal["Open", "In Process", "Won", "Lost", "Junk", "Pass to Other Partner"]
		territory: DF.Data | None
	# end: auto-generated types

	dashboard_fields = (
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
	)
