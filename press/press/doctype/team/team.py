# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import random_string, get_url


class Team(Document):
	def validate(self):
		# validate duplicate team members
		team_members = [row.user for row in self.team_members]
		duplicate_members = [m for m in team_members if team_members.count(m) > 1]
		duplicate_members = list(set(duplicate_members))
		if duplicate_members:
			frappe.throw(
				_("Duplicate Team Members: {0}").format(", ".join(duplicate_members)),
				frappe.DuplicateEntryError,
			)

		# set default user
		if not self.user and self.team_members:
			self.user = self.team_members[0].user

	def create_user_for_member(
		self, first_name=None, last_name=None, email=None, password=None, role=None
	):
		user = frappe.db.get_value("User", email, ["name"], as_dict=True)
		if not user:
			user = frappe.new_doc("User")
			user.first_name = first_name
			user.last_name = last_name
			user.email = email
			user.owner = email
			user.new_password = password
			user.append_roles(role)
			user.flags.no_welcome_mail = True
			user.save(ignore_permissions=True)

		self.append("team_members", {"user": user.name})

		if not self.enabled and role == "Press Admin":
			self.enabled = 1

		self.save(ignore_permissions=True)

	def add_team_member(self, email, owner=False):
		key = random_string(32)
		frappe.get_doc(
			{
				"doctype": "Account Request",
				"request_key": key,
				"team": self.name,
				"email": email,
				"role": "Press Admin" if owner else "Press Member",
			}
		).insert()

		url = get_url("/dashboard/#/setup-account/" + key)

		subject = "Verify your account"
		template = "verify_account"
		if not owner:
			subject = f"You are invited by {self.name} to join Frappe Cloud"
			template = "invite_team_member"

		frappe.sendmail(
			recipients=email, subject=subject, template=template, args={"link": url}, now=True,
		)


def get_team_members(team):
	if not frappe.db.exists("Team", team):
		return []

	r = frappe.db.get_all("Team Member", filters={"parent": team}, fields=["user"])
	member_emails = [d.user for d in r]

	users = []
	if member_emails:
		users = frappe.db.sql(
			"""
				select u.name, u.first_name, u.last_name, GROUP_CONCAT(r.`role`) as roles
				from `tabUser` u
				left join `tabHas Role` r
				on (r.parent = u.name)
				where ifnull(u.name, '') in %s
				group by u.name
			""",
			[member_emails],
			as_dict=True,
		)
		for user in users:
			user.roles = user.roles.split(",")

	return users


def get_default_team(user):
	if frappe.db.exists("Team", user):
		return user
