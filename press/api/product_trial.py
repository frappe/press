from __future__ import annotations

import frappe
from frappe.core.utils import find

from press.api.account import get_account_request_from_key
from press.press.doctype.team.team import Team
from press.utils.telemetry import capture


def _get_active_site(product: str, team: str) -> str | None:
	product_trial_linked_sites = frappe.get_all(
		"Product Trial Request",
		{"product_trial": product, "team": team, "status": ["not in", ["Pending", "Error", "Expired"]]},
		pluck="site",
	)
	if not product_trial_linked_sites:
		return None
	existing_sites = frappe.get_all(
		"Site",
		{
			"name": ["in", product_trial_linked_sites],
			"status": ["!=", "Archived"],
		},
		pluck="name",
		limit=1,
	)
	if len(existing_sites) > 0:
		return existing_sites[0]
	return None


@frappe.whitelist(allow_guest=True)
def signup(
	first_name: str,
	last_name: str,
	email: str,
	country: str,
	product: str,
	terms_accepted: bool,
	referrer=None,
):
	if not terms_accepted:
		frappe.throw("Please accept the terms and conditions")
	frappe.utils.validate_email_address(email, True)
	email = email.strip().lower()
	# validate country
	all_countries = frappe.db.get_all("Country", pluck="name")
	country = find(all_countries, lambda x: x.lower() == country.lower())
	if not country:
		frappe.throw("Please provide a valid country name")

	# add validation
	if frappe.db.exists("Team", {"user": email}) and _get_active_site(
		product, frappe.db.get_value("Team", {"user": email}, "name")
	):
		frappe.throw(f"You have already signed up for {product}. Instead try to log in.")

	# create account request
	account_request = frappe.get_doc(
		{
			"doctype": "Account Request",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"country": country,
			"role": "Press Admin",
			"saas": 1,
			"referrer_id": referrer,
			"product_trial": product,
			"send_email": True,
		}
	).insert(ignore_permissions=True)
	return account_request.name


@frappe.whitelist(allow_guest=True, methods=["POST"])
def setup_account(key: str):
	ar = get_account_request_from_key(key)
	if not ar:
		frappe.throw("Invalid or Expired Key")
	if not ar.product_trial:
		frappe.throw("Invalid Product Trial")
	frappe.set_user("Administrator")
	# check if team already exists
	if frappe.db.exists("Team", {"user": ar.email}):
		# Update first name and last name
		team = frappe.get_doc("Team", {"user": ar.email})
		team.first_name = ar.first_name
		team.last_name = ar.last_name
		team.save(ignore_permissions=True)
	# create team
	else:
		# check if user exists
		is_user_exists = frappe.db.exists("User", ar.email)
		team = Team.create_new(
			account_request=ar,
			first_name=ar.first_name,
			last_name=ar.last_name,
			country=ar.country,
			is_us_eu=ar.is_us_eu,
			user_exists=is_user_exists,
		)
	# Telemetry: Created account
	capture("completed_signup", "fc_saas", ar.email)
	# login
	frappe.set_user(ar.email)
	frappe.local.login_manager.login_as(ar.email)
	if _get_active_site(ar.product_trial, team.name):
		return {
			"location": f"/dashboard/saas/{ar.product_trial}/process",
		}

	return {
		"location": f"/dashboard/saas/{ar.product_trial}/setup",
	}


@frappe.whitelist(methods=["POST"])
def get_request(product):
	team = frappe.local.team()
	# validate if there is already a site
	site = _get_active_site(product, team.name)
	if site:
		site_request = frappe.get_doc(
			"Product Trial Request",
			{"product_trial": product, "team": team, "site": site},
			pluck="site",
		)
	else:
		# create a new one
		site_request = frappe.new_doc(
			"Product Trial Request",
			product_trial=product,
			team=team.name,
		).insert(ignore_permissions=True)

	return {
		"name": site_request.name,
		"site": site_request.site,
		"product_trial": site_request.product_trial,
		"status": site_request.status,
	}
