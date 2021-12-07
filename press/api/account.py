# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from typing import Union

import frappe
from frappe import _
from frappe.core.doctype.user.user import update_password
from frappe.exceptions import DoesNotExistError
from frappe.utils import get_url, random_string
from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
from frappe.website.utils import build_response
from frappe.core.utils import find

from press.press.doctype.team.team import Team, get_team_members
from press.utils import get_country_info, get_current_team


@frappe.whitelist(allow_guest=True)
def signup(email, referrer=None):
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
				"referrer_id": referrer,
			}
		).insert()

	frappe.set_user(current_user)


@frappe.whitelist(allow_guest=True)
def setup_account(
	key,
	first_name=None,
	last_name=None,
	password=None,
	is_invitation=False,
	country=None,
	user_exists=False,
):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	if not user_exists:
		if not first_name:
			frappe.throw("First Name is required")

		if not last_name:
			frappe.throw("Last Name is required")

		if not password:
			frappe.throw("Password is required")

		if not is_invitation and not country:
			frappe.throw("Country is required")

		if not is_invitation and country:
			all_countries = frappe.db.get_all("Country", pluck="name")
			country = find(all_countries, lambda x: x.lower() == country.lower())
			if not country:
				frappe.throw("Country filed should be a valid country name")

	# if the request is authenticated, set the user to Administrator
	frappe.set_user("Administrator")

	team = account_request.team
	email = account_request.email
	role = account_request.role

	if is_invitation:
		# if this is a request from an invitation
		# then Team already exists and will be added to that team
		doc = frappe.get_doc("Team", team)
		doc.create_user_for_member(first_name, last_name, email, password, role)
	else:
		# Team doesn't exist, create it
		Team.create_new(account_request, first_name, last_name, password, country=country)

	frappe.local.login_manager.login_as(email)


@frappe.whitelist(allow_guest=True)
def send_login_link(email):
	if not frappe.db.exists("User", email):
		frappe.throw("No registered account with this email address")

	key = frappe.generate_hash("Login Link", 20)
	minutes = 10
	frappe.cache().set_value(
		f"one_time_login_key:{key}", email, expires_in_sec=minutes * 60
	)

	link = get_url(f"/api/method/press.api.account.login_using_key?key={key}")

	if frappe.conf.developer_mode:
		print()
		print(f"One time login link for {email}")
		print(link)
		print()

	frappe.sendmail(
		subject="Login to Frappe Cloud",
		recipients=email,
		template="one_time_login_link",
		args={"link": link, "minutes": minutes},
		now=True,
	)


@frappe.whitelist(allow_guest=True)
def login_using_key(key):
	cache_key = f"one_time_login_key:{key}"
	email = frappe.cache().get_value(cache_key)

	if email:
		frappe.cache().delete_value(cache_key)
		frappe.local.login_manager.login_as(email)
		frappe.response.type = "redirect"
		frappe.response.location = "/dashboard"
	else:
		frappe.respond_as_web_page(
			_("Not Permitted"),
			_("The link using which you are trying to login is invalid or expired."),
			http_status_code=403,
			indicator_color="red",
		)


@frappe.whitelist()
def disable_account():
	team = get_current_team(get_doc=True)
	if frappe.session.user != team.name:
		frappe.throw("Only team owner can disable the account")
	team.disable_account()


@frappe.whitelist()
def enable_account():
	team = get_current_team(get_doc=True)
	if frappe.session.user != team.name:
		frappe.throw("Only team owner can enable the account")
	team.enable_account()


@frappe.whitelist()
def request_team_deletion():
	team = get_current_team()
	doc = frappe.get_doc({"doctype": "Team Deletion Request", "team": team}).insert()
	return doc.name


@frappe.whitelist(allow_guest=True)
def delete_team(team):
	from frappe.utils.verified_command import verify_request

	responses = {
		"invalid": [
			("Link Invalid", "This link is invalid or expired.",),
			{"indicator_color": "red"},
		],
		"confirmed": [
			(
				"Confirmed",
				f"The process for deletion of your team {team} has been initiated."
				" Sorry to see you go :(",
			),
			{"indicator_color": "green"},
		],
		"expired": [
			("Link Expired", "This link has already been activated for verification."),
			{"indicator_color": "red"},
		],
	}

	def respond_as_web_page(key):
		frappe.respond_as_web_page(*responses[key][0], **responses[key][1])

	if verify_request() or frappe.flags.in_test:
		frappe.set_user("Administrator")
	else:
		return respond_as_web_page("invalid")

	try:
		doc = frappe.get_last_doc("Team Deletion Request", {"team": team})
	except frappe.DoesNotExistError:
		return respond_as_web_page("invalid")

	if doc.status != "Pending Verification":
		return respond_as_web_page("expired")

	doc.status = "Deletion Verified"
	doc.save()
	frappe.db.commit()

	return respond_as_web_page("confirmed")


@frappe.whitelist(allow_guest=True)
def get_email_from_request_key(key):
	account_request = get_account_request_from_key(key)
	if account_request:
		data = get_country_info()
		return {
			"email": account_request.email,
			"country": data.get("country"),
			"user_exists": frappe.db.exists("User", account_request.email),
			"team": account_request.team,
			"is_invitation": frappe.db.get_value("Team", account_request.team, "enabled"),
		}


@frappe.whitelist(allow_guest=True)
def country_list():
	def get_country_list():
		return frappe.db.get_all("Country", fields=["name", "code"])

	return frappe.cache().get_value("country_list", generator=get_country_list)


def clear_country_list_cache():
	frappe.cache().delete_value("country_list")


@frappe.whitelist()
def set_country(country):
	team = get_current_team()
	doc = frappe.get_doc("Team", team)
	doc.country = country
	doc.save()
	doc.create_stripe_customer()


def get_account_request_from_key(key):
	"""Find Account Request using `key` in the past 4 hours"""
	hours = 4
	result = frappe.db.get_all(
		"Account Request",
		filters={
			"request_key": key,
			"creation": (">", frappe.utils.add_to_date(None, hours=-hours)),
		},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)
	if result:
		return frappe.get_doc("Account Request", result[0])


@frappe.whitelist()
def get():
	user = frappe.session.user
	if not frappe.db.exists("User", user):
		frappe.throw(_("Account does not exist"))

	team = get_current_team()
	team_doc = frappe.get_doc("Team", team)

	teams = [
		d.parent for d in frappe.db.get_all("Team Member", {"user": user}, ["parent"])
	]
	return {
		"user": frappe.get_doc("User", user),
		"team": team_doc,
		"team_members": get_team_members(team),
		"teams": list(set(teams)),
		"onboarding": team_doc.get_onboarding(),
		"balance": team_doc.get_balance(),
	}


@frappe.whitelist()
def update_profile(first_name=None, last_name=None, email=None):
	if email:
		frappe.utils.validate_email_address(email, True)
	user = frappe.session.user
	doc = frappe.get_doc("User", user)
	doc.first_name = first_name
	doc.last_name = last_name
	doc.email = email
	doc.save(ignore_permissions=True)
	return doc


@frappe.whitelist()
def update_profile_picture():
	user = frappe.session.user
	_file = frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": "User",
			"attached_to_name": user,
			"attached_to_field": "user_image",
			"folder": "Home/Attachments",
			"file_name": frappe.local.uploaded_filename,
			"is_private": 0,
			"content": frappe.local.uploaded_file,
		}
	)
	_file.save(ignore_permissions=True)
	frappe.db.set_value("User", user, "user_image", _file.file_url)


@frappe.whitelist(allow_guest=True)
def send_reset_password_email(email):
	frappe.utils.validate_email_address(email, True)

	email = email.strip()
	key = random_string(32)
	if frappe.db.exists("User", email):
		frappe.db.set_value("User", email, "reset_password_key", key)
		url = get_url("/dashboard/reset-password/" + key)
		frappe.sendmail(
			recipients=email,
			subject="Reset Password",
			template="reset_password",
			args={"link": url},
			now=True,
		)
	else:
		frappe.throw("User {0} does not exist".format(email))


@frappe.whitelist(allow_guest=True)
def reset_password(key, password):
	return update_password(new_password=password, key=key)


@frappe.whitelist(allow_guest=True)
def get_user_for_reset_password_key(key):
	return frappe.db.get_value("User", {"reset_password_key": key}, "name")


@frappe.whitelist()
def add_team_member(email):
	frappe.utils.validate_email_address(email, True)

	team = get_current_team(True)
	frappe.get_doc(
		{
			"doctype": "Account Request",
			"team": team.name,
			"email": email,
			"role": "Press Member",
			"invited_by": team.user,
		}
	).insert()


@frappe.whitelist()
def switch_team(team):
	user_is_part_of_team = frappe.db.exists(
		"Team Member", {"parent": team, "user": frappe.session.user}
	)
	user_is_system_user = frappe.session.data.user_type == "System User"
	if user_is_part_of_team or user_is_system_user:
		return {
			"team": frappe.get_doc("Team", team),
			"team_members": get_team_members(team),
		}


@frappe.whitelist()
def get_billing_information():
	team = get_current_team(True)
	if team.billing_address:
		billing_details = frappe.get_doc("Address", team.billing_address).as_dict()
		billing_details.billing_name = team.billing_name
		return billing_details


@frappe.whitelist()
def update_billing_information(billing_details):
	billing_details = frappe._dict(billing_details)
	team = get_current_team(get_doc=True)
	team.update_billing_details(billing_details)


@frappe.whitelist()
def feedback(message, route=None):
	team = get_current_team()
	feedback = frappe.new_doc("Feedback")
	feedback.team = team
	feedback.message = message
	feedback.route = route
	feedback.insert(ignore_permissions=True)


@frappe.whitelist()
def user_prompts():
	team = get_current_team()
	doc = frappe.get_doc("Team", team)

	onboarding = doc.get_onboarding()
	if not onboarding["complete"]:
		return

	if not doc.billing_address:
		return [
			"UpdateBillingDetails",
			"Update your billing details so that we can show it in your monthly invoice.",
		]

	gstin, country = frappe.db.get_value(
		"Address", doc.billing_address, ["gstin", "country"]
	)
	if country == "India" and not gstin:
		return [
			"UpdateBillingDetails",
			"If you have a registered GSTIN number, you are required to update it, so"
			" that we can generate a GST Invoice.",
		]


def redirect_to(location):
	return build_response(
		frappe.local.request.path,
		"",
		301,
		{"Location": location, "Cache-Control": "no-store, no-cache, must-revalidate"},
	)


def get_frappe_io_auth_url() -> Union[str, None]:
	"""Get auth url for oauth login with frappe.io."""

	try:
		provider = frappe.get_last_doc(
			"Social Login Key", filters={"enable_social_login": 1, "provider_name": "Frappe"}
		)
	except DoesNotExistError:
		return

	if (
		provider.base_url
		and provider.client_id
		and get_oauth_keys(provider.name)
		and provider.get_password("client_secret")
	):
		return get_oauth2_authorize_url(provider.name, redirect_to="")
