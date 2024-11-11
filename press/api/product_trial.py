import frappe
from frappe.core.utils import find

from press.api.account import get_account_request_from_key
from press.press.doctype.team.team import Team
from press.utils import get_current_team
from press.utils.telemetry import capture


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

	# TODO add validation

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
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"/dashboard/saas/{ar.product_trial}/setup"


@frappe.whitelist()
def get_product_info(product: str):
	team = get_current_team()
	product = frappe.utils.cstr(product)
	site_request = frappe.db.get_value(
		"Product Trial Request",
		filters={
			"product_trial": product,
			"team": team,
			"status": ("in", ["Pending", "Wait for Site", "Completing Setup Wizard"]),
		},
		fieldname=["name", "status", "site"],
		as_dict=1,
	)
	if site_request:
		product_trial = frappe.db.get_value(
			"Product Trial", {"name": product}, ["name", "title", "logo", "domain"], as_dict=True
		)
		return {
			"title": product_trial.title,
			"logo": product_trial.logo,
			"domain": product_trial.domain,
			"site_request": site_request,
		}
	return None
