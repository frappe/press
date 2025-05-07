# Copyright (c) 2015, Web Notes and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import timedelta

import frappe
import rq
import rq.exceptions
import rq.timeouts
from frappe import _
from frappe.model.document import Document
from frappe.rate_limiter import rate_limit
from frappe.utils.make_random import get_random

from press.utils import log_error


class DripEmail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.module_setup_guide.module_setup_guide import ModuleSetupGuide

		condition: DF.Code | None
		content_type: DF.Literal["Rich Text", "Markdown", "HTML"]
		email_type: DF.Literal[
			"Drip", "Sign Up", "Subscription Activation", "Whitepaper Feedback", "Onboarding"
		]
		enabled: DF.Check
		message_html: DF.HTMLEditor | None
		message_markdown: DF.MarkdownEditor | None
		message_rich_text: DF.TextEditor | None
		module_setup_guide: DF.Table[ModuleSetupGuide]
		pre_header: DF.Data | None
		reply_to: DF.Data | None
		saas_app: DF.Link | None
		send_after: DF.Int
		send_after_payment: DF.Check
		send_by_consultant: DF.Check
		sender: DF.Data
		sender_name: DF.Data
		skip_sites_with_paid_plan: DF.Check
		subject: DF.SmallText
	# end: auto-generated types

	def send(self, site_name: str | None = None):
		if self.evaluate_condition(site_name) and self.email_type in ["Drip", "Sign Up"] and site_name:
			self.send_drip_email(site_name)

	def send_drip_email(self, site_name: str, email: str | None = None):
		site = frappe.get_doc("Site", site_name)
		if self.email_type == "Drip" and site.status in ["Pending", "Broken"]:
			return

		if not self.send_after_payment and site.has_paid:
			return

		account_request = frappe.get_doc("Account Request", site.account_request)
		if not email and account_request.unsubscribed_from_drip_emails:
			return

		if self.send_by_consultant:
			consultant = self.select_consultant(site)
		else:
			consultant = ""

		self.send_mail(
			context=dict(
				full_name=account_request.full_name,
				email=email or account_request.email,
				domain=site.host_name or site.name,
				consultant=consultant,
				site=site,
				account_request=account_request,
			),
			recipient=email or account_request.email,
		)

	def send_mail(self, context, recipient):
		# build the message
		message = frappe.render_template(self.message, context)
		account_request = context.get("account_request", "")
		app = frappe.db.get_value("Marketplace App", self.saas_app, ["title", "image"], as_dict=True)

		# add to queue
		frappe.sendmail(
			subject=self.subject,
			recipients=[recipient],
			sender=f"{self.sender_name} <{self.sender}>",
			reply_to=self.reply_to,
			reference_doctype="Drip Email",
			reference_name=self.name,
			unsubscribe_message="Unsubscribe",
			unsubscribe_method="api/method/press.press.doctype.drip_email.drip_email.unsubscribe",
			unsubscribe_params={"account_request": account_request.name},
			attachments=self.get_setup_guides(account_request),
			template="product_trial_email",
			args={"message": message, "title": app.title, "logo": app.image},
		)

	@property
	def message(self):
		if self.content_type == "Markdown":
			return frappe.utils.md_to_html(self.message_markdown)
		if self.content_type == "Rich Text":
			return self.message_rich_text
		return self.message_html

	def evaluate_condition(self, site_name: str) -> bool:
		"""
		Evaluate the condition to check if the email should be sent.
		"""
		if not self.condition:
			return True

		saas_app = frappe.get_doc("Marketplace App", self.saas_app)
		site_account_request = frappe.db.get_value("Site", site_name, "account_request")
		account_request = frappe.get_doc("Account Request", site_account_request)

		eval_locals = dict(
			app=saas_app,
			doc=self,
			account_request=account_request,
		)

		return frappe.safe_eval(self.condition, None, eval_locals)

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

	def get_setup_guides(self, account_request) -> list[dict[str, str]]:
		if not account_request:
			return []

		attachments = []
		for guide in self.module_setup_guide:
			if account_request.industry == guide.industry:
				attachments.append(
					frappe.db.get_value("File", {"file_url": guide.setup_guide}, ["name as fid"], as_dict=1)
				)

		return attachments

	@property
	def sites_to_send_drip(self):
		signup_date = frappe.utils.getdate() - timedelta(days=self.send_after)

		conditions = ""

		if self.saas_app:
			conditions += f'AND site.standby_for = "{self.saas_app}"'

		if self.skip_sites_with_paid_plan:
			paid_site_plans = frappe.get_all(
				"Site Plan", {"enabled": True, "is_trial_plan": False, "document_type": "Site"}, pluck="name"
			)

			if paid_site_plans:
				paid_site_plans_str = ", ".join(f"'{plan}'" for plan in paid_site_plans)
				conditions += f" AND site.plan NOT IN ({paid_site_plans_str})"

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
					account_request.unsubscribed_from_drip_emails = 0 AND
					DATE(account_request.creation) = "{signup_date}"
					{conditions}
			"""
		)
		return [t[0] for t in sites]  # site names

	def send_to_sites(self):
		sites = self.sites_to_send_drip
		for site in sites:
			try:
				# TODO: only send `Onboarding` mails to partners <19-04-21, Balamurali M> #
				self.send(site)
				frappe.db.commit()
			except rq.timeouts.JobTimeoutException:
				log_error(
					"Drip Email Timeout",
					drip_email=self.name,
					site=site,
					total_sites=len(self.sites),
				)
				frappe.db.rollback()
				return
			except Exception:
				frappe.db.rollback()
				log_error("Drip Email Error", drip_email=self.name, site=site)

	@frappe.whitelist()
	def send_test_email(self, site: str, email: str):
		"""Send test email to the given email address."""
		self.send_drip_email(site, email)


def send_drip_emails():
	"""Send out enabled drip emails."""
	drip_emails = frappe.db.get_all(
		"Drip Email", {"enabled": 1, "email_type": ("in", ("Drip", "Onboarding"))}
	)
	for drip_email_name in drip_emails:
		frappe.enqueue_doc(
			"Drip Email",
			drip_email_name,
			"send_to_sites",
			queue="long",
			job_id=f"drip_email_send_to_sites:{drip_email_name}",
			deduplicate=True,
		)


def send_welcome_email():
	"""Send welcome email to sites created in last 15 minutes."""
	welcome_drips = frappe.db.get_all("Drip Email", {"email_type": "Sign Up", "enabled": 1}, pluck="name")
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


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def unsubscribe(email: str, account_request: str) -> None:
	"""
	Unsubscribe from drip emails of a site.
	"""
	if not account_request or not email:
		return None

	is_unsubscribed = frappe.db.get_value("Account Request", account_request, "unsubscribed_from_drip_emails")
	if is_unsubscribed is None:  # no account request found
		return None

	site = frappe.db.get_value("Site", {"account_request": account_request}, ["host_name", "name"], as_dict=1)
	if is_unsubscribed:  # already unsubscribed
		return frappe.respond_as_web_page(
			_("Already Unsubscribed"),
			_(
				f"You have already unsubscribed from receiving emails related to the site {frappe.bold(site.host_name or site.name)}."
			),
			indicator_color="red",
		)

	frappe.db.set_value("Account Request", account_request, "unsubscribed_from_drip_emails", 1)
	frappe.db.commit()

	return frappe.respond_as_web_page(
		_("Unsubscribed"),
		_(
			f"You have been unsubscribed from receiving emails related to the site {frappe.bold(site.host_name or site.name)}."
		),
		indicator_color="green",
	)
