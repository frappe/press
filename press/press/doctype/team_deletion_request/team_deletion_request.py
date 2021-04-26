# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.verified_command import get_signed_params
from frappe.website.doctype.personal_data_deletion_request.personal_data_deletion_request import (
	PersonalDataDeletionRequest,
)
from frappe.core.utils import find


class TeamDeletionRequest(PersonalDataDeletionRequest):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.email = self.team

	def before_insert(self):
		self.validate_team_owner()
		self.validate_duplicate_request()

	def after_insert(self):
		self.add_deletion_steps()
		self.set_users_anonymized()

		url = self.generate_url_for_confirmation()

		frappe.sendmail(
			recipients=self.email,
			subject="Account Deletion Request",
			template="delete_team_confirmation",
			args={"team": self.team, "link": url},
			header=["Account Deletion Request", "green"],
			now=True,
		)

	def validate(self):
		self.validate_sites_states()
		self.finalize_pending_invoices()
		self.validate_outstanding_invoices()

	def on_update(self):
		self.finish_up()

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

	@dont_throw
	@commit_after_execute
	def disable_team(self):
		team = self.team_doc
		team.enabled = False
		team.save()
		self.team_disabled = True
		self.save()
		self.reload()

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
		self.reload()

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

		self.save()
		frappe.db.commit()
		self.reload()

	@dont_throw
	@commit_after_execute
	def delete_data_on_press(self):
		deleted = True

		if not self.users_anonymized:
			self.set_users_anonymized()

		def is_deletion_pending(email):
			return find(
				self.users_anonymized,
				lambda x: x["team_member"] == email and x["deletion_status"] == "Pending",
			)

		for user in self.users_anonymized:
			now = user["team_member"]
			then = user["anon_team_member"]

			if is_deletion_pending(now):
				el = find(self.users_anonymized, lambda x: x["team_member"] == now)
				self.users_anonymized.remove(el)

				try:
					self._anonymize_data(now, then, commit=True)
					self.append(
						"users_anonymized",
						{"team_member": then, "anon_team_member": then, "deletion_status": "Deleted"},
					)
					self.save()
					frappe.db.commit()
				except Exception:
					frappe.db.rollback()
					self.append("users_anonymized", el)
					self.save()
					deleted = False

		self.db_set("data_anonymized", deleted, commit=True)
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
