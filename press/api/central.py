# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from press.api.account import get_account_request_from_key
from press.api.site import new as new_site


@frappe.whitelist(allow_guest=True)
def account_request(subdomain, email, first_name, last_name, phone_number, country):
	frappe.utils.validate_email_address(email, True)

	current_user = frappe.session.user
	frappe.set_user("Administrator")

	email = email.strip().lower()
	exists, enabled = frappe.db.get_value("Team", email, ["name", "enabled"]) or [0, 0]

	if exists and not enabled:
		frappe.throw(_("Account {0} has been deactivated").format(email))
	elif exists and enabled:
		frappe.throw(_("Account {0} is already registered").format(email))
	else:
		frappe.get_doc(
			{
				"doctype": "Account Request",
				"email": email,
				"role": "Press Admin",
				"first_name": first_name,
				"last_name": last_name,
				"phone_number": phone_number,
				"country": country,
				"subdomain": subdomain,
			}
		).insert()

	frappe.set_user(current_user)


@frappe.whitelist(allow_guest=True)
def setup_account(key):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	# if the request is authenticated, set the user to Administrator
	frappe.set_user("Administrator")

	team = account_request.team
	email = account_request.email
	role = account_request.role

	team_doc = frappe.get_doc(
		{
			"doctype": "Team",
			"name": team,
			"user": email,
			"country": account_request.country,
			"enabled": 1,
		}
	)
	team_doc.insert(ignore_permissions=True, ignore_links=True)

	print(account_request)

	team_doc.create_user_for_member(
		account_request.first_name, account_request.last_name, email, role=role
	)
	team_doc.create_stripe_customer()

	frappe.set_user(team_doc.user)

	# create site
	new_site(
		{
			"name": account_request.subdomain,
			"group": "bench-0001",
			"plan": "ERPNext Cloud",
			"apps": ["frappe", "erpnext"],
		}
	)


@frappe.whitelist(allow_guest=True)
def is_site_ready(subdomain):
	site = frappe.db.get_value("Site", {"subdomain": subdomain}, ["status", "subdomain"])
	return site
