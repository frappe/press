# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.verified_command import get_signed_params
from frappe.website.doctype.personal_data_deletion_request.personal_data_deletion_request import (
	PersonalDataDeletionRequest,
)
from frappe.core.utils import find


def handle_exception(self):
	frappe.db.rollback()
	traceback = f"<br><br><pre><code>{frappe.get_traceback()}</pre></code>"
	self.add_comment(text=f"Failure occurred during Data Deletion:{traceback}")
	frappe.db.commit()


class TeamDeletionRequest(PersonalDataDeletionRequest):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.email = self.team
		# turn off data deletions in partial content for the sake of sanity
		self.full_match_privacy_docs += self.partial_privacy_docs
		self.partial_privacy_docs = []

	def before_insert(self):
		self.validate_team_owner()
		self.validate_duplicate_request()

	def after_insert(self):
		self.add_deletion_steps()
		self.set_users_anonymized()

	def validate(self):
		self.validate_sites_states()
		self.finalize_pending_invoices()
		self.validate_outstanding_invoices()

	def on_update(self):
		self.finish_up()

	def handle_exc(foo):
		def after_execute(self):
			try:
				foo(self)
			except Exception:
				handle_exception(self)

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

	def validate_team_owner(self):
		if (
			self.team_doc.user == frappe.session.user or "System Manager" in frappe.get_roles()
		):
			return

		frappe.throw(
			"You need to be a Team owner to request account deletion", exc=frappe.PermissionError
		)

	def validate_duplicate_request(self):
		if frappe.db.exists(self.doctype, {"team": self.team}):
			frappe.throw(
				f"{self.doctype} for {self.team} already exists!", exc=frappe.DuplicateEntryError
			)

	def delete_team_data(self):
		self.db_set("status", "Processing Deletion")
		if not self.team_disabled:
			self.disable_team()
		if not self.frappeio_data_deleted:
			self.delete_data_on_frappeio()
		if not self.stripe_data_deleted:
			self.delete_stripe_customer()
		if (
			self.team_disabled and self.frappeio_data_deleted and self.stripe_data_deleted
		) and not self.data_anonymized:
			self.delete_data_on_press()
		self.finish_up()

	def finish_up(self):
		if (
			self.team_disabled
			and self.frappeio_data_deleted
			and self.stripe_data_deleted
			and self.data_anonymized
		):
			self.db_set("status", "Deleted")
			self.rename_team_on_data_deletion()
			frappe.db.commit()
			self.reload()

	def generate_url_for_confirmation(self):
		params = get_signed_params({"team": self.team})
		api = frappe.utils.get_url("/api/method/press.api.account.delete_team")
		url = f"{api}?{params}"

		if frappe.conf.developer_mode:
			print(f"URL generated for {self.doctype} {self.name}: {url}")

		return url

	@handle_exc
	def disable_team(self):
		team = self.team_doc
		team.enabled = False
		team.save()
		self.db_set("team_disabled", True, commit=True)
		self.reload()

	@handle_exc
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
		self.db_set("stripe_data_deleted", True, commit=True)
		self.reload()

	@handle_exc
	def delete_data_on_frappeio(self):
		"""Anonymize data on frappe.io"""
		from press.utils.billing import get_frappe_io_connection

		client = get_frappe_io_connection()
		response = client.session.delete(
			f"{client.url}/api/method/delete-fc-team",
			data={"team": self.team},
			headers=client.headers,
		)
		if not response.ok:
			response.raise_for_status()

		self.db_set("frappeio_data_deleted", True, commit=True)
		self.reload()

	def set_users_anonymized(self):
		def numerate_email(x, i):
			user_email, domain = x.split("@")
			return f"{user_email}-{i + 1}@{domain}"

		team_members = [row.user for row in self.team_doc.team_members]
		members_only_in_this_team = [
			user
			for user in team_members
			if not frappe.db.exists(
				"Team Member", {"user": user, "parent": ("!=", self.team_doc.name)}
			)
		]

		renamed_dict = {
			x: numerate_email(self.name, i) for i, x in enumerate(members_only_in_this_team)
		}

		for now, then in renamed_dict.items():
			self.append(
				"users_anonymized",
				{"team_member": now, "anon_team_member": then, "deletion_status": "Pending"},
			)

		self.db_update()
		self.update_children()
		frappe.db.commit()
		self.reload()

	@handle_exc
	def delete_data_on_press(self):
		if not self.users_anonymized:
			self.set_users_anonymized()

		def is_deletion_pending(email):
			return find(
				self.users_anonymized,
				lambda x: x.get("team_member") == email and x.get("deletion_status") == "Pending",
			)

		for user in self.users_anonymized:
			now = user.get("team_member")
			then = user.get("anon_team_member")

			if now == then and is_deletion_pending(now):
				# user has been anonymized. set status as deleted
				pass
			elif is_deletion_pending(now):
				self._anonymize_data(now, then, commit=True)
			else:
				continue

			try:
				self.users_anonymized = filter(
					lambda x: (x.get("team_member") != now) and (x.get("anon_team_member") != then),
					self.users_anonymized,
				)
				self.append(
					"users_anonymized",
					{"team_member": then, "anon_team_member": then, "deletion_status": "Deleted"},
				)
				self.db_update()
				self.update_children()
			except Exception:
				handle_exception(self)

			frappe.db.commit()

		self.db_set("data_anonymized", True, commit=True)
		self.reload()

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
			or_filters={"docstatus": 0, "status": "Draft"},
			pluck="name",
		)
		for invoice in pending_invoices:
			frappe.get_doc("Invoice", invoice).finalize_invoice()

	def validate_outstanding_invoices(self):
		if self.team_doc.is_defaulter():
			frappe.throw("You have Unpaid Invoices. Clear them to delete your account")


def process_team_deletion_requests():
	# order in desc since deleting press data takes the most time
	doctype = "Team Deletion Request"
	deletion_requests = frappe.get_all(
		doctype,
		filters={"status": ("in", ["Deletion Verified", "Processing Deletion"])},
		pluck="name",
		order_by="creation desc",
	)
	for name in deletion_requests:
		try:
			tdr = frappe.get_doc(doctype, name)
			tdr.delete_team_data()
			frappe.db.commit()
		except Exception:
			continue
