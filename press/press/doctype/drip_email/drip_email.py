# -*- coding: utf-8 -*-
# Copyright (c) 2015, Web Notes and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from datetime import date, timedelta
from typing import Dict, List

import frappe
from frappe.model.document import Document
from frappe.utils.make_random import get_random

from press.utils import log_error


class DripEmail(Document):
	def send(self, site_name=None, lead=None):
		if self.email_type in ["Drip", "Sign Up"] and site_name:
			self.send_drip_email(site_name)

		# TODO:  <19-04-21, Balamurali M> #
		# elif self.email_type == "Whitepaper Feedback" and lead:
		# 	self._consultant = frappe.get_doc("ERPNext Consultant", lead.consultant)
		# 	self.sender = self._consultant.email
		# 	self.sender_name = self._consultant.full_name
		# 	self.send_mail(context=lead, recipient=lead.email)

	def send_drip_email(self, site_name):
		site = frappe.get_doc("Site", site_name)
		if self.email_type == "Drip" and site.status in ["Pending", "Broken"]:
			return

		# TODO:  <19-04-21, Balamurali M> #
		# if not self.send_after_payment and site.subscription_status == "Paid":
		# customer has paid, don't send drip :-)
		# return

		# TODO:  <15-04-21, Balamurali M> #
		# if self.maximum_activation_level and site.activation > self.maximum_activation_level:
		# 	# user is already activated, quit
		# 	return

		account_request = frappe.get_doc("Account Request", {"subdomain": site.subdomain})
		if not account_request:
			log_error("Account Request not found", message=f"{site.name}")
			return

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

		# prepend preheader text to the start of the message
		if self.pre_header:
			message = (
				frappe.render_template(
					"press/press/doctype/drip_email/templates/pre_header.html",
					{"pre_header": self.pre_header},
					is_path=True,
				)
				+ message
			)

		# add to queue
		frappe.sendmail(
			subject=self.subject,
			recipients=[recipient],
			message=message,
			sender=f"{self.sender_name} <{self.sender}>",
			reply_to=self.reply_to,
			reference_doctype="Drip Email",
			reference_name=self.name,
			unsubscribe_message="Don't send me help messages",
			attachments=self.get_setup_guides(context.get("account_request", "")),
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
	def sites_to_send_mail(self):
		signup_date = date.today() - timedelta(days=self.send_after)
		sites = frappe.db.sql(
			f"""
				SELECT site.name
				FROM
					tabSite site
				JOIN
					`tabAccount Request` account_request
				ON
					account_request.subdomain = site.subdomain
				WHERE
					account_request.erpnext = True and
					DATE(site.creation) = "{signup_date}"
			"""
		)
		sites = [t[0] for t in sites]
		return sites

	def send_to_sites(self):
		for site in self.sites_to_send_mail:
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
