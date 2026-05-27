# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import Any

import frappe
from frappe.model.document import Document

from press.guards import role_guard
from press.utils import get_current_team


class PartnerOnboarding(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText | None
		agreed_to_due_diligence: DF.Check
		agreed_to_partnership_agreement: DF.Check
		annual_revenue: DF.Currency
		certified_employees_range: DF.Data | None
		company_email: DF.Data
		company_name: DF.Data
		contact: DF.Phone
		customer_count_range: DF.Data | None
		employee_range: DF.Data | None
		erp_implementations_range: DF.Data | None
		erpnext_customer_count_range: DF.Data | None
		existing_partnerships: DF.SmallText | None
		headquarter_city: DF.Data | None
		incorporation_certificate: DF.Attach | None
		registered_country: DF.Link
		revenue_currency: DF.Link | None
		status: DF.Literal["Draft", "Submission Pending", "Approved", "Rejected"]
		submitted_on: DF.Datetime | None
		team: DF.Link
		verticals_served: DF.SmallText | None
	# end: auto-generated types

	dashboard_fields = (
		"team",
		"company_name",
		"registered_country",
		"company_email",
		"contact",
		"address",
		"headquarter_city",
		"annual_revenue",
		"revenue_currency",
		"employee_range",
		"certified_employees_range",
		"verticals_served",
		"customer_count_range",
		"erpnext_customer_count_range",
		"existing_partnerships",
		"erp_implementations_range",
		"incorporation_certificate",
		"agreed_to_due_diligence",
		"agreed_to_partnership_agreement",
	)


def _get_partner_onboarding(team: str):
	name = frappe.db.get_value("Partner Onboarding", {"team": team}, "name")
	if name:
		return frappe.get_doc("Partner Onboarding", name)
	return None


@frappe.whitelist()
@role_guard.api("partner")
def get_partner_onboarding() -> dict | None:
	team = get_current_team(get_doc=True)
	doc = _get_partner_onboarding(team.name)
	if not doc:
		return None
	return doc.as_dict()


@frappe.whitelist(methods=["POST"])
@role_guard.api("partner")
def save_partner_onboarding(details: dict[str, Any]) -> dict:
	team = get_current_team(get_doc=True)
	details = frappe._dict(details)
	doc = _get_partner_onboarding(team.name)

	if not doc:
		doc = frappe.get_doc(
			{
				"doctype": "Partner Onboarding",
				"team": team.name,
				"status": "Draft",
			}
		)

	for fieldname in PartnerOnboarding.dashboard_fields:
		if fieldname in ("team", "status"):
			continue
		if fieldname in details:
			doc.set(fieldname, details[fieldname])

	if not doc.name:
		doc.insert()
	else:
		doc.save()

	return doc.as_dict()
