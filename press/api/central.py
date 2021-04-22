# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

from press.press.doctype.site.erpnext_site import ERPNextSite, get_erpnext_domain
import frappe
from frappe.geo.country_info import get_country_timezone_info
from frappe.utils.data import get_url
from press.api.account import get_account_request_from_key
from press.utils.billing import get_erpnext_com_connection
from press.press.doctype.site.erpnext_site import get_erpnext_plan
from press.press.doctype.site.pool import get as get_pooled_site


@frappe.whitelist(allow_guest=True)
def account_request(
	subdomain, email, first_name, last_name, phone_number, country, url_args=None
):
	email = email.strip().lower()
	frappe.utils.validate_email_address(email, True)

	if not check_subdomain_availability(subdomain):
		frappe.throw(f"Subdomain {subdomain} is already taken")

	account_request = frappe.get_doc(
		{
			"doctype": "Account Request",
			"erpnext": True,
			"subdomain": subdomain,
			"email": email,
			"role": "Press Admin",
			"first_name": first_name,
			"last_name": last_name,
			"phone_number": phone_number,
			"country": country,
			"url_args": url_args,
		}
	).insert(ignore_permissions=True)

	current_user = frappe.session.user
	current_session_data = frappe.session.data
	frappe.set_user("Administrator")

	try:
		pooled_site = get_pooled_site()
		if pooled_site:
			# Rename a standby site
			ERPNextSite(site=pooled_site).rename_pooled_site(account_request)
		else:
			# Create a new site if pooled sites aren't available
			ERPNextSite(account_request=account_request).insert(ignore_permissions=True)
	finally:
		frappe.set_user(current_user)
		frappe.session.data = current_session_data


@frappe.whitelist(allow_guest=True)
def setup_account(key, business_data=None):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	frappe.set_user("Administrator")

	if business_data:
		business_data = frappe.parse_json(business_data)

	if isinstance(business_data, dict):
		business_data = {
			key: business_data.get(key)
			for key in [
				"company",
				"no_of_employees",
				"industry",
				"no_of_users",
				"designation",
				"referral_source",
			]
		}

	account_request.update(business_data)
	account_request.save(ignore_permissions=True)

	team = account_request.team
	email = account_request.email
	role = account_request.role

	if not frappe.db.exists("Team", email):
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
	else:
		team_doc = frappe.get_doc("Team", email)

	site_name = frappe.db.get_value("Site", {"account_request": account_request.name})
	site = frappe.get_doc("Site", site_name)
	site.team = team_doc.name
	site.save()

	subscription = site.subscription
	if subscription:
		subscription.team = team_doc.name
		subscription.save()

	frappe.set_user(team_doc.user)
	frappe.local.login_manager.login_as(team_doc.user)

	return site.name


@frappe.whitelist(allow_guest=True)
def get_site_status(key):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	site = frappe.db.get_value(
		"Site",
		{"subdomain": account_request.subdomain, "domain": get_erpnext_domain()},
		["status", "subdomain"],
		as_dict=1,
	)
	if site:
		return site
	else:
		return {"status": "Pending"}


@frappe.whitelist()
def get_site_url_and_sid(key):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	name = frappe.db.get_value(
		"Site", {"subdomain": account_request.subdomain, "domain": get_erpnext_domain()},
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

	exists = frappe.db.exists(
		"Site", {"subdomain": subdomain, "domain": get_erpnext_domain()}
	)
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


@frappe.whitelist(allow_guest=True)
def get_trial_end_date(site):
	return frappe.db.get_value("Site", site, "trial_end_date")


@frappe.whitelist(allow_guest=True)
def send_login_link(site):
	if not frappe.db.exists("Site", site):
		frappe.throw("Invalid site")

	from press.api.account import send_login_link as send_link

	# send link to site owner
	email = frappe.db.get_value("Site", site, "team")
	send_link(email)
	return email
