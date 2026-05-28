# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url


class CertificateLinkRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		course: DF.Data | None
		key: DF.Data | None
		partner: DF.Data | None
		partner_team: DF.Link | None
		status: DF.Literal["Approved", "Cancelled", "Pending"]
		user_email: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		self.status = "Pending"
		self.partner = frappe.db.get_value("Team", self.partner_team, "company_name")
		self.key = frappe.generate_hash(15)

	def on_update(self):
		self.publish_status_update()

		if self.status == "Approved" and self.has_value_changed("status"):
			self.link_certificate()

	def after_insert(self):
		self.send_validation_email()
		self.publish_status_update()

	def send_validation_email(self):
		link = get_url(f"/api/method/press.api.partner.approve_certificate_link_request?key={self.key}")

		frappe.sendmail(
			recipients=[self.user_email],
			subject="Certificate Link Request",
			template="partner_link_certificate",
			args={"link": link, "partner": self.partner or "", "user": self.user_email},
			now=True,
		)

	def resend(self):
		# A resend must invalidate any older email link for this request.
		self.key = frappe.generate_hash(15)
		self.save()
		self.send_validation_email()
		self.publish_status_update()

	def link_certificate(self):
		certificate = self.get_certificate(self.user_email, self.course)
		if not certificate:
			frappe.throw("Certificate linked to this request was not found.")
		if certificate.team and certificate.team != self.partner_team:
			frappe.throw("This certificate is already linked to another partner team.")

		frappe.db.set_value(
			"Partner Certificate",
			certificate.name,
			"team",
			self.partner_team,
		)

	def publish_status_update(self):
		frappe.publish_realtime(
			"partner_onboarding_certificates_updated",
			message={"team": self.partner_team},
			doctype="Team",
			after_commit=True,
		)

	@staticmethod
	def get_certificate(user_email: str, course: str):
		certificates = frappe.get_all(
			"Partner Certificate",
			filters={"partner_member_email": user_email, "course": course},
			fields=["name", "team", "course", "partner_member_email", "partner_member_name"],
			limit=1,
		)
		return certificates[0] if certificates else None

	@classmethod
	def resolve_certificate(cls, user_email: str, certificate_type: str):
		certificate_courses = {
			"frappe": ["frappe-developer-certification", "app-development-with-frappe-framework"],
			"erpnext": ["erpnext-distribution", "erpnext-training"],
		}

		courses = certificate_courses.get(certificate_type, certificate_courses["frappe"])
		certificates = frappe.get_all(
			"Partner Certificate",
			filters={"partner_member_email": user_email, "course": ("in", courses)},
			fields=["name", "team", "course", "partner_member_email", "partner_member_name"],
			order_by="issue_date desc",
			limit=1,
		)
		return certificates[0] if certificates else None

	@classmethod
	def create_or_resend(cls, partner_team: str, user_email: str, certificate_type: str):
		certificate = cls.resolve_certificate(user_email, certificate_type)
		if not certificate:
			frappe.throw(f"No certificate found for {user_email}.")

		if certificate.team == partner_team:
			return {"status": "Linked", "certificate": certificate}

		if certificate.team:
			frappe.throw("This certificate is already linked to another partner team.")

		existing_request = frappe.db.get_value(
			"Certificate Link Request",
			{
				"partner_team": partner_team,
				"user_email": user_email,
				"course": certificate.course,
				"status": "Pending",
			},
			"name",
		)
		if existing_request:
			doc = frappe.get_doc("Certificate Link Request", existing_request)
			doc.resend()
			return {"status": "Pending", "request": doc.as_dict()}

		doc = frappe.get_doc(
			{
				"doctype": "Certificate Link Request",
				"partner_team": partner_team,
				"user_email": user_email,
				"course": certificate.course,
			}
		)
		doc.insert()
		return {"status": "Pending", "request": doc.as_dict()}

	@classmethod
	def approve_from_key(cls, key: str):
		name = frappe.db.get_value("Certificate Link Request", {"key": key}, "name")
		if not name:
			frappe.throw("Invalid or expired certificate link request.")

		doc = frappe.get_doc("Certificate Link Request", name)
		if doc.status != "Pending":
			frappe.throw("Certificate link request has already been approved.")

		if doc.user_email != frappe.session.user:
			frappe.throw("Please log in with the email address attached to this certificate.")

		doc.status = "Approved"
		doc.save()
		return doc
