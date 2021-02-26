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

	@property
	def team_doc(self):
		return frappe.get_cached_doc("Team", self.team)

	def before_insert(self):
		if frappe.db.exists(self.doctype, self.team):
			frappe.throw(
				f"{self.doctype} for {self.team} already exists!", exc=frappe.DuplicateEntryError
			)

	def validate(self):
		self.validate_sites_states()
		self.validate_outstanding_invoices()
		self.trigger_data_deletion()

	def on_update(self):
		if self.status == "Deleted" and self.name != self.team:
			frappe.rename_doc("Team", self.team, self.name)

	def trigger_data_deletion(self):
		if self.status == "Processing Deletion":
			if not self.team_disabled:
				self.disable_team()
			if not self.frappeio_data_deleted:
				self.delete_data_on_frappeio()
			if not self.stripe_data_deleted:
				self.delete_stripe_customer()
			if not self.data_anonymized:
				self.delete_data_on_press()
			self.finish_up()

	def finish_up(self):
		self.db_set("status", "Deleted", update_modified=False, commit=True)

	def generate_url_for_confirmation(self):
		params = get_signed_params({"team": self.team})
		api = frappe.utils.get_url("/api/method/press.api.account.delete_team")
		return f"{api}?{params}"

	def disable_team(self):
		team = self.team_doc
		team.enabled = False
		team.save()
		self.db_set("team_disabled", True, update_modified=False, commit=True)

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
		self.db_set("stripe_data_deleted", True, update_modified=False, commit=True)

	def delete_data_on_frappeio(self):
		"""Anonymize data on frappe.io"""
		from press.utils.billing import get_frappe_io_connection
		client = get_frappe_io_connection()
		response = client.session.delete(
			f"{client.url}/api/method/delete-fc-team",
			data={"team": self.team},
		)
		if response.ok:
			self.db_set("frappeio_data_deleted", True, update_modified=False, commit=True)

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

		self.db_set("data_anonymized", True, update_modified=False, commit=True)

	def validate_sites_states(self):
		non_archived_sites = frappe.get_all(
			"Site", filters={"status": ("!=", "Archived"), "team": self.team}, pluck="name"
		)
		if non_archived_sites:
			frappe.throw(
				f"Team {self.team} has {len(non_archived_sites)} sites. Drop them"
				" before you can delete your account"
			)

	def validate_outstanding_invoices(self):
		if self.team_doc.is_defaulter():
			frappe.throw(f"You have Unpaid Invoices. Clear them to delete your account")
