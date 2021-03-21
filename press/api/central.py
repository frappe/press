# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.geo.country_info import get_country_timezone_info
from press.api.account import get_account_request_from_key
from press.api.site import new as new_site
from press.utils.billing import get_erpnext_com_connection

# ERPNEXT_DOMAIN = "erpnext.com"
ERPNEXT_DOMAIN = "frappe.cloud"


@frappe.whitelist(allow_guest=True)
def account_request(subdomain, email, first_name, last_name, phone_number, country):
	frappe.utils.validate_email_address(email, True)

	if not check_subdomain_availability(subdomain):
		frappe.throw(f"Subdomain {subdomain} is already taken")

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
				"erpnext": True,
				"email": email,
				"role": "Press Admin",
				"first_name": first_name,
				"last_name": last_name,
				"phone_number": phone_number,
				"country": country,
				"subdomain": subdomain,
			}
		).insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def setup_account(key, business_data=None):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	business_data = {
		key: business_data.get(key)
		for key in ["domain", "users", "company", "designation", "referral_source"]
	}

	account_request.update(business_data)
	account_request.save()

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
def get_site_status(key):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	site = frappe.db.get_value(
		"Site",
		{"subdomain": account_request.subdomain, "domain": ERPNEXT_DOMAIN},
		["status", "subdomain"],
		as_dict=1,
	)
	return site


@frappe.whitelist(allow_guest=True)
def get_site_url_and_sid(key):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	name = frappe.db.get_value(
		"Site", {"subdomain": account_request.subdomain, "domain": ERPNEXT_DOMAIN},
	)
	site = frappe.get_doc("Site", name)
	return {
		"url": f"https://{site.name}",
		"sid": site.login(),
	}


@frappe.whitelist(allow_guest=True)
def check_subdomain_availability(subdomain):
	erpnext_com = get_erpnext_com_connection()

	result = erpnext_com.post_api(
		"central.www.signup.check_subdomain_availability", {"subdomain": subdomain}
	)
	if result:
		return False

	exists = frappe.db.exists("Site", {"subdomain": subdomain, "domain": ERPNEXT_DOMAIN})
	if exists:
		return False

	return True


@frappe.whitelist(allow_guest=True)
def options_for_regional_data(key):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	data = {
		"languages": frappe.db.get_all("Language", ["language_name", "language_code"]),
		"currencies": frappe.db.get_all("Currency", pluck="name"),
		"country": account_request.country,
	}
	data.update(get_country_timezone_info())

	return data
