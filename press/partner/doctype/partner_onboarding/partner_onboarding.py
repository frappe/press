# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from press.api.client import dashboard_whitelist
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
		contact: DF.Phone | None
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
		"status",
		"submitted_on",
	)

	def validate(self):
		if self.status == "Submission Pending":
			self.validate_submission()

	def validate_submission(self):
		required_fields = {
			"company_name": "Company name",
			"registered_country": "Registered country",
			"company_email": "Company email",
			"contact": "Contact",
			"address": "Address",
			"headquarter_city": "Headquarter city",
		}
		missing = [label for fieldname, label in required_fields.items() if not self.get(fieldname)]
		if missing:
			frappe.throw(f"Please complete these fields before submitting: {', '.join(missing)}")

		if not self.agreed_to_due_diligence:
			frappe.throw("Please confirm due diligence before submitting.")
		if not self.agreed_to_partnership_agreement:
			frappe.throw("Please accept the Partnership agreement before submitting.")

	def before_save(self):
		if self.status == "Submission Pending" and not self.submitted_on:
			self.submitted_on = now_datetime()

	@dashboard_whitelist()
	def submit_for_approval(self):
		self.status = "Submission Pending"
		self.save()


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
		if fieldname in ("team", "status", "submitted_on"):
			continue
		if fieldname in details:
			doc.set(fieldname, details[fieldname])

	if not doc.name:
		doc.insert()
	else:
		doc.save()

	return doc.as_dict()


@frappe.whitelist(methods=["POST"])
@role_guard.api("partner")
def submit_partner_onboarding(details: dict[str, Any] | None = None) -> dict:
	if details:
		doc = save_partner_onboarding(details)
		onboarding = frappe.get_doc("Partner Onboarding", doc["name"])
	else:
		team = get_current_team(get_doc=True)
		onboarding = _get_partner_onboarding(team.name)
		if not onboarding:
			frappe.throw("Please register as a partner before submitting for approval.")

	onboarding.submit_for_approval()
	frappe.db.commit()
	return onboarding.as_dict()


@frappe.whitelist()
@role_guard.api("partner")
def get_partner_onboarding_status() -> dict:
	team = get_current_team(get_doc=True)
	certificates = frappe.get_all(
		"Partner Certificate",
		filters={"team": team.name},
		fields=["name", "course", "partner_member_email", "partner_member_name"],
	)
	certificate_requests = frappe.get_all(
		"Certificate Link Request",
		filters={"partner_team": team.name},
		fields=["name", "course", "user_email", "status", "creation"],
		order_by="creation desc",
	)
	return {
		"certificates": certificates,
		"certificate_requests": certificate_requests,
		"linked_certificate_count": len(certificates),
	}


@frappe.whitelist(methods=["POST"])
@role_guard.api("partner")
def send_link_certificate_request(user_email: str, certificate_type: str) -> None:
	from press.api.partner import send_link_certificate_request as send_request

	return send_request(user_email=user_email, certificate_type=certificate_type)


@frappe.whitelist()
@role_guard.api("partner")
def check_certificate_exists(email: str, certificate_type: str) -> int:
	from press.api.partner import check_certificate_exists as check_exists

	return check_exists(email=email, certificate_type=certificate_type)
