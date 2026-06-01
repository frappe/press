# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import Any

import frappe
from frappe.model.document import Document
from frappe.utils import flt, get_last_day, now_datetime, today
from pypika.enums import Order

from press.guards import role_guard
from press.partner.doctype.certificate_link_request.certificate_link_request import CertificateLinkRequest
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
		amended_from: DF.Link | None
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
		incorporation_certificate: DF.Data | None
		registered_country: DF.Link
		rejection_reason: DF.SmallText | None
		revenue_currency: DF.Link | None
		reviewed_by: DF.Link | None
		reviewed_on: DF.Datetime | None
		status: DF.Literal["Draft", "Pending Review", "Approved", "Rejected", "Cancelled"]
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

	def before_submit(self):
		team = frappe.get_cached_doc("Team", self.team)

		if not _is_profile_complete(self):
			frappe.throw(
				"Complete your company profile before submitting for approval."
			)  # nosemgrep: error is self-explanatory

		if not _get_certificate_link_status(self.team)["requirement_complete"]:
			frappe.throw(
				"Link at least two certificates before submitting for approval."
			)  # nosemgrep: error is self-explanatory

		if not _get_mrr_status(team)["requirement_complete"]:
			frappe.throw(
				"Reach the minimum MRR before submitting for approval."
			)  # nosemgrep: error is self-explanatory

		self.status = "Pending Review"
		self.submitted_on = now_datetime()

	@frappe.whitelist()
	def approve(self):
		frappe.only_for("Partner Manager")

		if self.docstatus != 1:
			frappe.throw("Submit this partner onboarding request before approval.")

		if self.status != "Pending Review":
			frappe.throw(
				"Only pending submissions can be approved. Refresh the page and open a pending review request."
			)

		team = frappe.get_doc("Team", self.team)
		team.enable_erpnext_partner_privileges()

		self.status = "Approved"
		self.reviewed_by = frappe.session.user
		self.reviewed_on = now_datetime()
		self.rejection_reason = None
		self.save()
		# publish a realtime event to update the partner onboarding status
		frappe.publish_realtime(
			"partner_onboarding_status_updated",
			message={"team": self.team},
			doctype="Team",
			after_commit=True,
		)

	@frappe.whitelist()
	def reject(self, reason: str | None = None):
		frappe.only_for("Partner Manager")

		if self.docstatus != 1:
			frappe.throw(
				"Submit this partner onboarding request before rejection."
			)  # nosemgrep: error is self-explanatory

		if self.status != "Pending Review":
			frappe.throw(
				"Only pending submissions can be rejected. Refresh the page and open a pending review request."
			)

		self.status = "Rejected"
		self.reviewed_by = frappe.session.user
		self.reviewed_on = now_datetime()
		self.rejection_reason = reason
		self.save()
		# publish a realtime event to update the partner onboarding status
		frappe.publish_realtime(
			"partner_onboarding_status_updated",
			message={"team": self.team},
			doctype="Team",
			after_commit=True,
		)


def _get_partner_onboarding(team: str):
	names = frappe.get_all(
		"Partner Onboarding",
		filters={"team": team, "docstatus": ["<", 2], "status": ["!=", "Cancelled"]},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)
	if names:
		return frappe.get_doc("Partner Onboarding", names[0])
	return None


def _clear_certificate_links(team: str) -> None:
	for certificate in frappe.get_all(
		"Partner Certificate",
		filters={"team": team},
		pluck="name",
	):
		frappe.db.set_value("Partner Certificate", certificate, "team", None)

	for request in frappe.get_all(
		"Certificate Link Request",
		filters={"partner_team": team, "status": "Pending"},
		pluck="name",
	):
		frappe.db.set_value(
			"Certificate Link Request",
			request,
			{"status": "Cancelled", "key": None},
		)

	frappe.publish_realtime(
		"partner_onboarding_certificates_updated",
		message={"team": team},
		user=frappe.session.user,
		after_commit=True,
	)


def _get_certificate_link_status(team: str) -> dict:
	partner_certificate = frappe.qb.DocType("Partner Certificate")
	certificate_link_request = frappe.qb.DocType("Certificate Link Request")

	linked_certificates = (
		frappe.qb.from_(partner_certificate)
		.select(
			partner_certificate.name,
			partner_certificate.course,
			partner_certificate.partner_member_email.as_("user_email"),
			partner_certificate.partner_member_name.as_("member_name"),
		)
		.where(partner_certificate.team == team)
		.orderby(partner_certificate.creation, order=Order.desc)
		.run(as_dict=True)
	)
	link_requests = (
		frappe.qb.from_(certificate_link_request)
		.select(
			certificate_link_request.name,
			certificate_link_request.course,
			certificate_link_request.user_email,
			certificate_link_request.status,
			certificate_link_request.creation,
		)
		.where(
			(certificate_link_request.partner_team == team)
			& (certificate_link_request.status.isin(["Pending", "Approved"]))
		)
		.orderby(certificate_link_request.creation, order=Order.desc)
		.run(as_dict=True)
	)
	pending_requests = [request for request in link_requests if request.status == "Pending"]
	linked_count = len(linked_certificates)

	return {
		"linked_certificates": linked_certificates,
		"link_requests": link_requests,
		"pending_requests": pending_requests,
		"linked_count": linked_count,
		"requirement_complete": linked_count >= 2,
	}


def _get_mrr_status(team) -> dict:
	team_currency = team.currency or "USD"
	target_amount = 10000 if team_currency == "INR" else 100

	invoice = frappe.qb.DocType("Invoice")
	invoices = (
		frappe.qb.from_(invoice)
		.select(invoice.currency, invoice.total_before_discount)
		.where(
			(invoice.partner_email == team.partner_email)
			& (invoice.due_date == get_last_day(today()))
			& (invoice.type == "Subscription")
			& (invoice.docstatus == 1)
		)
		.run(as_dict=True)
	)

	current_amount = 0
	for row in invoices:
		if team_currency == row.currency:
			current_amount += row.total_before_discount
		elif team_currency == "USD":
			current_amount += flt(row.total_before_discount / 83, 2)
		else:
			current_amount += flt(row.total_before_discount * 83, 2)

	return {
		"current_amount": flt(current_amount, 2),
		"target_amount": target_amount,
		"currency": team_currency,
		"progress": min(100, flt((current_amount / target_amount) * 100, 2)) if target_amount else 0,
		"requirement_complete": current_amount >= target_amount,
	}


def _is_profile_complete(doc: PartnerOnboarding) -> bool:
	return all(
		[
			doc.company_name,
			doc.registered_country,
			doc.company_email,
			doc.contact,
			doc.address,
			doc.headquarter_city,
			doc.agreed_to_due_diligence,
			doc.agreed_to_partnership_agreement,
		]
	)


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
	elif doc.docstatus != 0:
		frappe.throw(
			"Submitted partner onboarding details cannot be changed. Contact partner support if you need to update them."
		)

	for fieldname in PartnerOnboarding.dashboard_fields:
		if fieldname in ("team", "status"):
			continue
		if fieldname in details:
			value = details[fieldname]
			if fieldname in ("verticals_served", "existing_partnerships") and isinstance(value, list):
				value = ", ".join(str(item).strip() for item in value if str(item).strip())
			doc.set(fieldname, value)

	if not doc.name:
		doc.insert()
	else:
		doc.save()

	return doc.as_dict()


@frappe.whitelist()
@role_guard.api("partner")
def get_certificate_link_status() -> dict:
	team = get_current_team(get_doc=True)
	return _get_certificate_link_status(team.name)


@frappe.whitelist()
@role_guard.api("partner")
def get_mrr_status() -> dict:
	team = get_current_team(get_doc=True)
	return _get_mrr_status(team)


@frappe.whitelist(methods=["POST"])
@role_guard.api("partner")
def submit_for_approval() -> dict:
	team = get_current_team(get_doc=True)
	doc = _get_partner_onboarding(team.name)
	if not doc:
		frappe.throw(
			"Register as a partner before submitting for approval."
		)  # nosemgrep: error is self-explanatory

	if doc.docstatus == 1:
		return doc.as_dict()

	if doc.docstatus != 0:
		frappe.throw(
			"This partner onboarding request cannot be submitted. Register again to start a new request."
		)

	doc.submit()
	return doc.as_dict()


@frappe.whitelist(methods=["POST"])
@role_guard.api("partner")
def unregister() -> None:
	team = get_current_team(get_doc=True)
	doc = _get_partner_onboarding(team.name)
	if not doc:
		return

	if doc.status == "Approved":
		frappe.get_doc("Team", team.name).disable_erpnext_partner_privileges()

	_clear_certificate_links(team.name)

	if doc.docstatus == 1:
		doc.cancel()
	elif doc.docstatus == 0:
		# delete the partner onboarding request from the database as it was not submitted for approval and in draft state
		frappe.delete_doc("Partner Onboarding", doc.name)


@frappe.whitelist(methods=["POST"])
@role_guard.api("partner")
def send_certificate_link_request(user_email: str, certificate_type: str) -> dict:
	team = get_current_team(get_doc=True)
	return CertificateLinkRequest.create_or_resend(team.name, user_email, certificate_type)


@frappe.whitelist(methods=["POST"])
@role_guard.api("partner")
def resend_certificate_link_request(request_name: str) -> dict:
	team = get_current_team(get_doc=True)
	doc = frappe.get_doc("Certificate Link Request", request_name)

	if doc.partner_team != team.name:
		frappe.throw(
			"This certificate link request does not belong to your team. Open a request from your team's onboarding page."
		)

	if doc.status != "Pending":
		frappe.throw(
			"Only pending certificate link requests can be resent. Refresh the page and open a pending request."
		)

	doc.resend()
	return doc.as_dict()
