# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.press.doctype.account_request.account_request import AccountRequest
from press.press.doctype.team.team import Team


class Org(Document):
	@classmethod
	def create_new(
		cls,
		account_request: AccountRequest,
		first_name: str,
		last_name: str,
		password: str = None,
		country: str = None,
		is_us_eu: bool = False,
		via_erpnext: bool = False,
		user_exists: bool = False,
	):
		"""Create new team along with user (user created first)."""
		org = frappe.get_doc(
			{
				"doctype": "Org",
				"name": account_request.team,
				"user": account_request.email,
				"country": country,
				"enabled": 1,
				"via_erpnext": via_erpnext,
				"is_us_eu": is_us_eu,
			}
		)

		if not user_exists:
			user = org.create_user(
				first_name, last_name, account_request.email, password, account_request.role
			)
		else:
			user = frappe.get_doc("User", account_request.email)
			user.append_roles(account_request.role)
			user.save(ignore_permissions=True)

		Team.create_new(account_request)
		org.append("members", {"user": user.name})
		org.insert()
		return org

	@staticmethod
	def create_user(first_name=None, last_name=None, email=None, password=None, role=None):
		user = frappe.new_doc("User")
		user.first_name = first_name
		user.last_name = last_name
		user.email = email
		user.owner = email
		user.new_password = password
		user.append_roles(role)
		user.flags.no_welcome_mail = True
		user.save(ignore_permissions=True)
		return user
