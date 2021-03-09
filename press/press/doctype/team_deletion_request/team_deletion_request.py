# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.verified_command import get_signed_params
from frappe.website.doctype.personal_data_deletion_request.personal_data_deletion_request import (
	PersonalDataDeletionRequest,
)


class TeamDeletionRequest(PersonalDataDeletionRequest):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.email = self.team

	def before_insert(self):
		self.validate_duplicate_request()

	def after_insert(self):
		url = self.generate_url_for_confirmation()

		frappe.sendmail(
			recipients=self.email,
			subject="Account Deletion Request",
			template="delete_team_confirmation",
			args={"team": self.team, "link": url},
			header=["Account Deletion Request", "green"],
		)

	def validate(self):
		self.validate_sites_states()
		self.finalize_pending_invoices()
		self.validate_outstanding_invoices()

	def dont_throw(foo):
		def pass_exception(self):
			try:
				foo(self)
			except Exception:
				frappe.db.rollback()

				traceback = f"<br><br><pre><code>{frappe.get_traceback()}</pre></code>"
				self.add_comment(text=f"Failure occurred during Data Deletion:{traceback}")

				frappe.db.commit()

		return pass_exception

	def commit_after_execute(foo):
		def after_execute(self):
			try:
				foo(self)
			except Exception:
				pass
			else:
				frappe.db.commit()

		return after_execute

	@property
	def team_doc(self):
		return frappe.get_cached_doc("Team", self.team)

	def rename_team_on_data_deletion(self):
		if (
			self.status == "Deleted"
			and self.name != self.team
			and frappe.db.exists("Team", self.team)
		):
			frappe.rename_doc("Team", self.team, self.name)

	def validate_duplicate_request(self):
		if frappe.db.exists(self.doctype, {"team": self.team}):
			frappe.throw(
				f"{self.doctype} for {self.team} already exists!", exc=frappe.DuplicateEntryError
			)

	def delete_team_data(self):
		if self.status == "Processing Deletion":
			if not self.team_disabled:
				self.disable_team()
			if not self.frappeio_data_deleted:
				self.delete_data_on_frappeio()
			if not self.stripe_data_deleted:
				self.delete_stripe_customer()
			if (
				True
				or (self.team_disabled and self.frappeio_data_deleted and self.stripe_data_deleted)
				and not self.data_anonymized
			):
				self.delete_data_on_press()
			self.finish_up()

	def finish_up(self):
		if (
			self.team_disabled
			and self.frappeio_data_deleted
			and self.stripe_data_deleted
			and self.data_anonymized
		):
			self.status = "Deleted"
			self.save()
			self.reload()
			self.rename_team_on_data_deletion()

	def generate_url_for_confirmation(self):
		params = get_signed_params({"team": self.team})
		api = frappe.utils.get_url("/api/method/press.api.account.delete_team")
		url = f"{api}?{params}"

		if frappe.conf.developer_mode:
			print(f"URL generated for {self.doctype} {self.name}: {url}")

		return url

	@dont_throw
	@commit_after_execute
	def disable_team(self):
		team = self.team_doc
		team.enabled = False
		team.save()
		self.team_disabled = True
		self.save()

	@dont_throw
	@commit_after_execute
	def delete_stripe_customer(self):
		from press.api.billing import get_stripe

		stripe = get_stripe()
		team = self.team_doc

		try:
			stripe.Customer.delete(team.stripe_customer_id)
		except stripe.error.InvalidRequestError as e:
			if "No such customer" not in str(e):
				raise e

		team.db_set("stripe_customer_id", False)
		self.stripe_data_deleted = True
		self.save()

	@dont_throw
	@commit_after_execute
	def delete_data_on_frappeio(self):
		"""Anonymize data on frappe.io"""
		from press.utils.billing import get_frappe_io_connection

		client = get_frappe_io_connection()
		response = client.session.delete(
			f"{client.url}/api/method/delete-fc-team", data={"team": self.team},
		)
		if not response.ok:
			response.raise_for_status()

		self.frappeio_data_deleted = True
		self.save()

	@dont_throw
	@commit_after_execute
	def delete_data_on_press(self):
		# 1. rename team and team members to whatever else
		team_members = [row.user for row in self.team_doc.team_members]
		members_only_in_this_team = [
			user
			for user in team_members
			if not frappe.db.exists(
				"Team Member", {"user": user, "parent": ("!=", self.team_doc.name)}
			)
		]

		def numerate_email(x, i):
			user_email, domain = x.split("@")
			return f"{user_email}-{i + 1}@{domain}"

		renamed_dict = {
			x: numerate_email(self.name, i) for i, x in enumerate(members_only_in_this_team)
		}

		for now, then in renamed_dict.items():
			self._anonymize_data(now, then)

		self.data_anonymized = True
		self.save()

	def validate_sites_states(self):
		non_archived_sites = frappe.get_all(
			"Site", filters={"status": ("!=", "Archived"), "team": self.team}, pluck="name"
		)
		if non_archived_sites:
			frappe.throw(
				f"Team {self.team} has {len(non_archived_sites)} sites. Drop them"
				" before you can delete your account"
			)

	def finalize_pending_invoices(self):
		pending_invoices = frappe.get_all(
			"Invoice",
			filters={"team": self.team},
			or_filters={"docstatus": 1, "status": "Draft"},
			pluck="name",
		)
		for invoice in pending_invoices:
			frappe.get_doc("Invoice", invoice).finalize_invoice()

	def validate_outstanding_invoices(self):
		if self.team_doc.is_defaulter():
			frappe.throw(f"You have Unpaid Invoices. Clear them to delete your account")


def process_team_deletion_requests():
	doctype = "Team Deletion Request"
	for name in frappe.get_all(
		doctype,
		filters={"status": ("in", ["Deletion Verified", "Processing Deletion"])},
		pluck="name",
	):
		tdr = frappe.get_doc(doctype, name)
		tdr.status = "Processing Deletion"
		tdr.delete_team_data()
		tdr.reload()
		tdr.save()
