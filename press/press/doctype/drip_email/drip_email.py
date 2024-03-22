# -*- coding: utf-8 -*-
# Copyright (c) 2015, Web Notes and contributors
# For license information, please see license.txt


from datetime import timedelta
from typing import Dict, List

import frappe
from frappe.model.document import Document
from frappe.utils.make_random import get_random


class DripEmail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.module_setup_guide.module_setup_guide import ModuleSetupGuide

		distribution: DF.Check
		education: DF.Check
		email_type: DF.Literal[
			"Drip", "Sign Up", "Subscription Activation", "Whitepaper Feedback", "Onboarding"
		]
		enabled: DF.Check
		healthcare: DF.Check
		manufacturing: DF.Check
		maximum_activation_level: DF.Int
		message: DF.TextEditor
		minimum_activation_level: DF.Int
		module_setup_guide: DF.Table[ModuleSetupGuide]
		non_profit: DF.Check
		other: DF.Check
		pre_header: DF.Data | None
		reply_to: DF.Data | None
		retail: DF.Check
		saas_app: DF.Link | None
		send_after: DF.Int
		send_after_payment: DF.Check
		send_by_consultant: DF.Check
		sender: DF.Data
		sender_name: DF.Data
		services: DF.Check
		subject: DF.SmallText
	# end: auto-generated types

	def send(self, site_name=None, lead=None):
		if self.email_type in ["Drip", "Sign Up"] and site_name:
			self.send_drip_email(site_name)

	def send_drip_email(self, site_name):
		site = frappe.get_doc("Site", site_name)
		if self.email_type == "Drip" and site.status in ["Pending", "Broken"]:
			return

		if not self.send_after_payment and site.has_paid:
			return

		account_request = frappe.get_doc("Account Request", site.account_request)

		if self.send_by_consultant:
			consultant = self.select_consultant(site)
		else:
			consultant = ""

		self.send_mail(
			context=dict(
				full_name=account_request.full_name,
				email=account_request.email,
				domain=site.name,
				consultant=consultant,
				site=site,
				account_request=account_request,
			),
			recipient=account_request.email,
		)

	def send_mail(self, context, recipient):
		# build the message
		message = frappe.render_template(self.message, context)
		title = frappe.db.get_value("Marketplace App", self.saas_app, "title")

		# add to queue
		frappe.sendmail(
			subject=self.subject,
			recipients=[recipient],
			sender=f"{self.sender_name} <{self.sender}>",
			reply_to=self.reply_to,
			reference_doctype="Drip Email",
			reference_name=self.name,
			unsubscribe_message="Don't send me help messages",
			attachments=self.get_setup_guides(context.get("account_request", "")),
			template="drip_email",
			args={"message": message, "title": title},
		)

	def select_consultant(self, site) -> str:
		"""
		Select random ERPNext Consultant to send email.

		Also set sender details.
		"""
		if not site.erpnext_consultant:
			# set a random consultant for the site for the first time
			site.erpnext_consultant = get_random("ERPNext Consultant", dict(active=1))
			frappe.db.set_value("Site", site.name, "erpnext_consultant", site.erpnext_consultant)

		consultant = frappe.get_doc("ERPNext Consultant", site.erpnext_consultant)
		self.sender = consultant.name
		self.sender_name = consultant.full_name
		return consultant

	def get_setup_guides(self, account_request) -> List[Dict[str, str]]:
		if not account_request:
			return []

		attachments = []
		for guide in self.module_setup_guide:
			if account_request.industry == guide.industry:
				attachments.append(
					frappe.db.get_value(
						"File", {"file_url": guide.setup_guide}, ["name as fid"], as_dict=1
					)
				)

		return attachments

	@property
	def sites_to_send_drip(self):
		signup_date = frappe.utils.getdate() - timedelta(days=self.send_after)

		conditions = ""

		if self.saas_app:
			conditions += f'AND site.standby_for = "{self.saas_app}"'

		sites = frappe.db.sql(
			f"""
				SELECT
					site.name
				FROM
					tabSite site
				JOIN
					`tabAccount Request` account_request
				ON
					site.account_request = account_request.name
				WHERE
					site.status = "Active" AND
					DATE(account_request.creation) = "{signup_date}"
					{conditions}
			"""
		)
		sites = [t[0] for t in sites]
		return sites

	def send_to_sites(self):
		for site in self.sites_to_send_drip:
			self.send(site)
			# TODO: only send `Onboarding` mails to partners <19-04-21, Balamurali M> #


def send_drip_emails():
	"""Send out enabled drip emails."""
	drip_emails = frappe.db.get_all(
		"Drip Email", {"enabled": 1, "email_type": ("in", ("Drip", "Onboarding"))}
	)
	for drip_email_name in drip_emails:
		drip_email = frappe.get_doc("Drip Email", drip_email_name)
		drip_email.send_to_sites()


def send_welcome_email():
	"""Send welcome email to sites created in last 15 minutes."""
	welcome_drips = frappe.db.get_all(
		"Drip Email", {"email_type": "Sign Up", "enabled": 1}, pluck="name"
	)
	for drip in welcome_drips:
		welcome_email = frappe.get_doc("Drip Email", drip)
		_15_mins_ago = frappe.utils.add_to_date(None, minutes=-15)
		tuples = frappe.db.sql(
			f"""
				SELECT
					site.name
				FROM
					tabSite site
				JOIN
					`tabAccount Request` account_request
				ON
					site.account_request = account_request.name
				WHERE
					site.status = "Active" and
					site.standby_for = "{welcome_email.saas_app}" and
					account_request.creation > "{_15_mins_ago}"
			"""
		)
		sites_in_last_15_mins = [t[0] for t in tuples]
		for site in sites_in_last_15_mins:
			welcome_email.send(site)
