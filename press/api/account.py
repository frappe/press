# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
import pyotp
from frappe import _
from frappe.core.doctype.user.user import update_password
from frappe.core.utils import find
from frappe.exceptions import DoesNotExistError
from frappe.query_builder.custom import GROUP_CONCAT
from frappe.rate_limiter import rate_limit
from frappe.utils import get_url
from frappe.utils.data import sha256_hash
from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
from frappe.utils.password import get_decrypted_password
from frappe.website.utils import build_response
from pypika.terms import ValueWrapper

from press.api.site import protected
from press.press.doctype.team.team import (
	Team,
	get_child_team_members,
	get_team_members,
	has_active_servers,
	has_unsettled_invoices,
)
from press.utils import get_country_info, get_current_team, is_user_part_of_team
from press.utils.telemetry import capture

if TYPE_CHECKING:
	from press.press.doctype.account_request.account_request import AccountRequest


@frappe.whitelist(allow_guest=True)
def signup(email, product=None, referrer=None):
	frappe.utils.validate_email_address(email, True)

	current_user = frappe.session.user
	frappe.set_user("Administrator")

	email = email.strip().lower()
	exists, enabled = frappe.db.get_value("Team", {"user": email}, ["name", "enabled"]) or [0, 0]

	account_request = None
	if exists and not enabled:
		frappe.throw(_("Account {0} has been deactivated").format(email))
	elif exists and enabled:
		frappe.throw(_("Account {0} is already registered").format(email))
	else:
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"email": email,
				"role": "Press Admin",
				"referrer_id": referrer,
				"saas": bool(product),
				"product_trial": product,
				"send_email": True,
			}
		).insert()

	frappe.set_user(current_user)
	if account_request:
		return account_request.name
	return None

	return None


@frappe.whitelist(allow_guest=True)
def verify_otp(account_request: str, otp: str):
	account_request: "AccountRequest" = frappe.get_doc("Account Request", account_request)
	# ensure no team has been created with this email
	if not account_request.product_trial and frappe.db.exists("Team", {"user": account_request.email}):
		frappe.throw("Invalid OTP. Please try again.")
	if account_request.otp != otp:
		frappe.throw("Invalid OTP. Please try again.")
	account_request.reset_otp()
	return account_request.request_key


@frappe.whitelist(allow_guest=True)
def resend_otp(account_request: str):
	account_request: "AccountRequest" = frappe.get_doc("Account Request", account_request)
	# ensure no team has been created with this email
	if not account_request.product_trial and frappe.db.exists("Team", {"user": account_request.email}):
		frappe.throw("Invalid Email")
	account_request.reset_otp()
	account_request.send_verification_email()


@frappe.whitelist(allow_guest=True)
def setup_account(  # noqa: C901
	key,
	first_name=None,
	last_name=None,
	password=None,
	is_invitation=False,
	country=None,
	user_exists=False,
	accepted_user_terms=False,
	invited_by_parent_team=False,
	oauth_signup=False,
	oauth_domain=False,
):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	if not user_exists:
		if not first_name:
			frappe.throw("First Name is required")

		if not password and not (oauth_signup or oauth_domain):
			frappe.throw("Password is required")

		if not is_invitation and not country:
			frappe.throw("Country is required")

		if not is_invitation and country:
			all_countries = frappe.db.get_all("Country", pluck="name")
			country = find(all_countries, lambda x: x.lower() == country.lower())
			if not country:
				frappe.throw("Please provide a valid country name")

	if not accepted_user_terms:
		frappe.throw("Please accept our Terms of Service & Privacy Policy to continue")

	# if the request is authenticated, set the user to Administrator
	frappe.set_user("Administrator")

	team = account_request.team
	email = account_request.email
	role = account_request.role
	press_roles = account_request.press_roles

	if is_invitation:
		# if this is a request from an invitation
		# then Team already exists and will be added to that team
		doc = frappe.get_doc("Team", team)
		doc.create_user_for_member(first_name, last_name, email, password, role, press_roles)
	else:
		# Team doesn't exist, create it
		team_doc = Team.create_new(
			account_request=account_request,
			first_name=first_name,
			last_name=last_name,
			password=password,
			country=country,
			user_exists=bool(user_exists),
		)
		if invited_by_parent_team:
			doc = frappe.get_doc("Team", account_request.invited_by)
			doc.append("child_team_members", {"child_team": team})
			doc.save()

		if account_request.product_trial:
			frappe.new_doc(
				"Product Trial Request",
				product_trial=account_request.product_trial,
				account_request=account_request.name,
				team=team_doc.name,
			).insert(ignore_permissions=True)

	# Telemetry: Created account
	capture("completed_signup", "fc_signup", account_request.email)
	frappe.local.login_manager.login_as(email)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def send_login_link(email):
	if not frappe.db.exists("User", email):
		frappe.throw("No registered account with this email address")

	key = frappe.generate_hash("Login Link", 20)
	minutes = 10
	frappe.cache().set_value(f"one_time_login_key:{key}", email, expires_in_sec=minutes * 60)

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
@rate_limit(limit=5, seconds=60 * 60)
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
def active_servers():
	team = get_current_team()
	return frappe.get_all("Server", {"team": team, "status": "Active"}, ["title", "name"])


@frappe.whitelist()
def disable_account(totp_code: str | None):
	user = frappe.session.user
	team = get_current_team(get_doc=True)

	if is_2fa_enabled(user):
		if not totp_code:
			frappe.throw("2FA Code is required")
		if not verify_2fa(user, totp_code):
			frappe.throw("Invalid 2FA Code")

	if user != team.user:
		frappe.throw("Only team owner can disable the account")
	if has_unsettled_invoices(team.name):
		return "Unpaid Invoices"
	if has_active_servers(team.name):
		return "Active Servers"

	team.disable_account()
	return None


@frappe.whitelist()
def enable_account():
	team = get_current_team(get_doc=True)
	if frappe.session.user != team.user:
		frappe.throw("Only team owner can enable the account")
	team.enable_account()


@frappe.whitelist()
def request_team_deletion():
	team = get_current_team(get_doc=True)
	doc = frappe.get_doc({"doctype": "Team Deletion Request", "team": team.name}).insert()
	return doc.name


@frappe.whitelist(allow_guest=True)
def delete_team(team):
	from frappe.utils.verified_command import verify_request

	responses = {
		"invalid": [
			("Link Invalid", "This link is invalid or expired."),
			{"indicator_color": "red"},
		],
		"confirmed": [
			(
				"Confirmed",
				f"The process for deletion of your team {team} has been initiated." " Sorry to see you go :(",
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
def validate_request_key(key, timezone=None):
	from press.utils.country_timezone import get_country_from_timezone

	account_request = get_account_request_from_key(key)
	if account_request:
		data = get_country_info()
		possible_country = data.get("country") or get_country_from_timezone(timezone)
		product_trial = frappe.db.get_value(
			"Product Trial",
			{"name": account_request.product_trial},
			pluck="name",
		)
		product_trial_doc = frappe.get_doc("Product Trial", product_trial) if product_trial else None
		if not (account_request.is_saas_signup() or account_request.invited_by_parent_team):
			capture("clicked_verify_link", "fc_signup", account_request.email)
		return {
			"email": account_request.email,
			"first_name": account_request.first_name,
			"last_name": account_request.last_name,
			"country": possible_country,
			"countries": frappe.db.get_all("Country", pluck="name"),
			"user_exists": frappe.db.exists("User", account_request.email),
			"team": account_request.team,
			"is_invitation": frappe.db.get_value("Team", account_request.team, "enabled"),
			"invited_by": account_request.invited_by,
			"invited_by_parent_team": account_request.invited_by_parent_team,
			"oauth_signup": account_request.oauth_signup,
			"oauth_domain": frappe.db.exists(
				"OAuth Domain Mapping", {"email_domain": account_request.email.split("@")[1]}
			),
			"product_trial": {
				"name": product_trial_doc.name,
				"title": product_trial_doc.title,
				"logo": product_trial_doc.logo,
				"signup_fields": product_trial_doc.signup_fields,
				"description": product_trial_doc.description,
			}
			if product_trial_doc
			else None,
		}
	return None

	return None


@frappe.whitelist(allow_guest=True)
def country_list():
	def get_country_list():
		return frappe.db.get_all("Country", fields=["name", "code"])

	return frappe.cache().get_value("country_list", generator=get_country_list)


def clear_country_list_cache():
	frappe.cache().delete_value("country_list")


@frappe.whitelist()
def set_country(country):
	team_doc = get_current_team(get_doc=True)
	team_doc.country = country
	team_doc.save()
	team_doc.create_stripe_customer()


def get_account_request_from_key(key):
	"""Find Account Request using `key` in the past 12 hours or if site is active"""

	if not key or not isinstance(key, str):
		frappe.throw(_("Invalid Key"))

	hours = 12
	ar = frappe.get_doc("Account Request", {"request_key": key})
	if ar.creation > frappe.utils.add_to_date(None, hours=-hours):
		return ar
	if ar.subdomain and ar.saas_app:
		domain = frappe.db.get_value("Saas Settings", ar.saas_app, "domain")
		if frappe.db.get_value("Site", ar.subdomain + "." + domain, "status") == "Active":
			return ar
	return None

	return None


@frappe.whitelist()
def get():
	cached = frappe.cache.get_value("cached-account.get", user=frappe.session.user)
	if cached:
		return cached
	value = _get()
	frappe.cache.set_value("cached-account.get", value, user=frappe.session.user, expires_in_sec=60)
	return value


def _get():
	user = frappe.session.user
	if not frappe.db.exists("User", user):
		frappe.throw(_("Account does not exist"))

	team_doc = get_current_team(get_doc=True)

	parent_teams = [d.parent for d in frappe.db.get_all("Team Member", {"user": user}, ["parent"])]

	teams = []
	if parent_teams:
		Team = frappe.qb.DocType("Team")
		teams = (
			frappe.qb.from_(Team)
			.select(Team.name, Team.team_title, Team.user)
			.where((Team.enabled == 1) & (Team.name.isin(parent_teams)))
			.run(as_dict=True)
		)

	partner_billing_name = ""
	if team_doc.partner_email:
		partner_billing_name = frappe.db.get_value(
			"Team",
			{"erpnext_partner": 1, "partner_email": team_doc.partner_email},
			"billing_name",
		)
	number_of_sites = frappe.db.count("Site", {"team": team_doc.name, "status": ("!=", "Archived")})

	return {
		"user": frappe.get_doc("User", user),
		"ssh_key": get_ssh_key(user),
		"team": team_doc,
		"team_members": get_team_members(team_doc.name),
		"child_team_members": get_child_team_members(team_doc.name),
		"teams": list(teams if teams else parent_teams),
		"onboarding": team_doc.get_onboarding(),
		"balance": team_doc.get_balance(),
		"parent_team": team_doc.parent_team or "",
		"saas_site_request": team_doc.get_pending_saas_site_request(),
		"feature_flags": {
			"verify_cards_with_micro_charge": frappe.db.get_single_value(
				"Press Settings", "verify_cards_with_micro_charge"
			)
		},
		"partner_email": team_doc.partner_email or "",
		"partner_billing_name": partner_billing_name,
		"number_of_sites": number_of_sites,
		"permissions": get_permissions(),
		"billing_info": team_doc.billing_info(),
	}


@frappe.whitelist()
def current_team():
	user = frappe.session.user
	if not frappe.db.exists("User", user):
		frappe.throw(_("Account does not exist"))

	from press.api.client import get

	return get("Team", frappe.local.team().name)


def get_permissions():
	user = frappe.session.user
	groups = tuple(
		[*frappe.get_all("Press Permission Group User", {"user": user}, pluck="parent"), "1", "2"]
	)  # [1, 2] is for avoiding singleton tuples
	docperms = frappe.db.sql(
		f"""
			SELECT `document_name`, GROUP_CONCAT(`action`) as `actions`
			FROM `tabPress User Permission`
			WHERE user='{user}' or `group` in {groups}
			GROUP BY `document_name`
		""",
		as_dict=True,
	)
	return {perm.document_name: perm.actions.split(",") for perm in docperms if perm.actions}


@frappe.whitelist()
def has_method_permission(doctype, docname, method) -> bool:
	from press.press.doctype.press_permission_group.press_permission_group import (
		has_method_permission,
	)

	return has_method_permission(doctype, docname, method)


@frappe.whitelist(allow_guest=True)
def signup_settings(product=None, fetch_countries=False, timezone=None):
	from press.utils.country_timezone import get_country_from_timezone

	settings = frappe.get_single("Press Settings")

	product = frappe.utils.cstr(product)
	product_trial = None
	if product:
		product_trial = frappe.db.get_value(
			"Product Trial",
			{"name": product, "published": 1},
			["title", "description", "logo"],
			as_dict=1,
		)

	data = {
		"enable_google_oauth": settings.enable_google_oauth,
		"product_trial": product_trial,
		"oauth_domains": frappe.get_all(
			"OAuth Domain Mapping", ["email_domain", "social_login_key", "provider_name"]
		),
	}

	if fetch_countries:
		data["countries"] = frappe.db.get_all("Country", pluck="name")
		data["country"] = get_country_info().get("country") or get_country_from_timezone(timezone)

	return data


@frappe.whitelist(allow_guest=True)
def guest_feature_flags():
	return {
		"enable_google_oauth": frappe.db.get_single_value("Press Settings", "enable_google_oauth"),
	}


@frappe.whitelist()
def create_child_team(title):
	team = title.strip()

	current_team = get_current_team(True)
	if title in [
		d.team_title for d in frappe.get_all("Team", {"parent_team": current_team.name}, ["team_title"])
	]:
		frappe.throw(f"Child Team {title} already exists.")
	elif title == "Parent Team":
		frappe.throw("Child team name cannot be same as parent team")

	doc = frappe.get_doc(
		{
			"doctype": "Team",
			"team_title": team,
			"user": current_team.user,
			"parent_team": current_team.name,
			"enabled": 1,
		}
	)
	doc.insert(ignore_permissions=True, ignore_links=True)
	doc.append("team_members", {"user": current_team.user})
	doc.save()

	current_team.append("child_team_members", {"child_team": doc.name})
	current_team.save()

	return "created"


def new_team(email, current_team):
	frappe.utils.validate_email_address(email, True)

	frappe.get_doc(
		{
			"doctype": "Account Request",
			"email": email,
			"role": "Press Member",
			"send_email": True,
			"team": email,
			"invited_by": current_team,
			"invited_by_parent_team": 1,
		}
	).insert()

	return "new_team"


def get_ssh_key(user):
	ssh_keys = frappe.get_all(
		"User SSH Key", {"user": user, "is_default": True}, order_by="creation desc", limit=1
	)
	if ssh_keys:
		return frappe.get_doc("User SSH Key", ssh_keys[0])

	return None


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


@frappe.whitelist()
def update_feature_flags(values=None):
	frappe.only_for("Press Admin")
	team = get_current_team(get_doc=True)
	values = frappe.parse_json(values)
	fields = [
		"benches_enabled",
		"servers_enabled",
		"self_hosted_servers_enabled",
		"security_portal_enabled",
	]
	for field in fields:
		if field in values:
			team.set(field, values[field])
	team.save()


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def send_reset_password_email(email: str):
	valid_email = frappe.utils.validate_email_address(email)
	if not valid_email:
		frappe.throw(
			f"{email} is not a valid email address",
			frappe.InvalidEmailAddressError,
		)

	valid_email = valid_email.strip()
	key = frappe.generate_hash()
	hashed_key = sha256_hash(key)
	if frappe.db.exists("User", valid_email):
		frappe.db.set_value(
			"User",
			valid_email,
			{
				"reset_password_key": hashed_key,
				"last_reset_password_key_generated_on": frappe.utils.now_datetime(),
			},
		)
		url = get_url("/dashboard/reset-password/" + key)
		if frappe.conf.developer_mode:
			print(f"\nReset password URL for {valid_email}:")
			print(url)
			print()
			return
		frappe.sendmail(
			recipients=valid_email,
			subject="Reset Password",
			template="reset_password",
			args={"link": url},
			now=True,
		)
	else:
		frappe.throw(f"User {valid_email} does not exist")


@frappe.whitelist(allow_guest=True)
def reset_password(key, password):
	return update_password(new_password=password, key=key)


@frappe.whitelist(allow_guest=True)
def get_user_for_reset_password_key(key):
	if not key or not isinstance(key, str):
		frappe.throw(_("Invalid Key"))

	hashed_key = sha256_hash(key)
	return frappe.db.get_value("User", {"reset_password_key": hashed_key}, "name")


@frappe.whitelist()
def remove_team_member(user_email):
	team = get_current_team(True)
	team.remove_team_member(user_email)


@frappe.whitelist()
def remove_child_team(child_team):
	team = frappe.get_doc("Team", child_team)
	sites = frappe.get_all("Site", {"status": ("!=", "Archived"), "team": team.name}, pluck="name")
	if sites:
		frappe.throw("Child team has Active Sites")

	team.enabled = 0
	team.parent_team = ""
	team.save(ignore_permissions=True)


@frappe.whitelist()
def can_switch_to_team(team):
	if not frappe.db.exists("Team", team):
		return False
	if frappe.local.system_user():
		return True
	if is_user_part_of_team(frappe.session.user, team):
		return True
	return False


@frappe.whitelist()
def switch_team(team):
	user_is_part_of_team = frappe.db.exists("Team Member", {"parent": team, "user": frappe.session.user})
	user_is_system_user = frappe.session.data.user_type == "System User"
	if user_is_part_of_team or user_is_system_user:
		frappe.db.set_value("Team", {"user": frappe.session.user}, "last_used_team", team)
		frappe.cache.delete_value("cached-account.get", user=frappe.session.user)
		return {
			"team": frappe.get_doc("Team", team),
			"team_members": get_team_members(team),
		}
	return None


@frappe.whitelist()
def leave_team(team):
	team_to_leave = frappe.get_doc("Team", team)
	cur_team = frappe.session.user

	if team_to_leave.user == cur_team:
		frappe.throw("Cannot leave this team as you are the owner.")

	team_to_leave.remove_team_member(cur_team)


@frappe.whitelist()
def get_billing_information(timezone=None):
	from press.utils.country_timezone import get_country_from_timezone

	team = get_current_team(True)

	billing_details = frappe._dict()
	if team.billing_address:
		billing_details = frappe.get_doc("Address", team.billing_address).as_dict()
		billing_details.billing_name = team.billing_name

	if not billing_details.country and timezone:
		billing_details.country = get_country_from_timezone(timezone)

	return billing_details


@frappe.whitelist()
def update_billing_information(billing_details):
	billing_details = frappe._dict(billing_details)
	team = get_current_team(get_doc=True)
	if (team.country != billing_details.country) and (
		team.country == "India" or billing_details.country == "India"
	):
		frappe.throw("Cannot change country after registration")
	team.update_billing_details(billing_details)


@frappe.whitelist()
def feedback(team, message, note, rating, route=None):
	feedback = frappe.new_doc("Press Feedback")
	feedback.team = team
	feedback.message = message
	feedback.note = note
	feedback.route = route
	feedback.rating = rating / 5
	feedback.insert(ignore_permissions=True)


@frappe.whitelist()
def get_site_count(team):
	return frappe.db.count("Site", {"team": team, "status": ("=", "Active")})


@frappe.whitelist()
def user_prompts():
	if frappe.local.dev_server:
		return None

	team = get_current_team(True)
	doc = frappe.get_doc("Team", team.name)

	onboarding = doc.get_onboarding()
	if not onboarding["complete"]:
		return None

	if not doc.billing_address:
		return [
			"UpdateBillingDetails",
			"Update your billing details so that we can show it in your monthly invoice.",
		]

	gstin, country = frappe.db.get_value("Address", doc.billing_address, ["gstin", "country"])
	if country == "India" and not gstin:
		return [
			"UpdateBillingDetails",
			"If you have a registered GSTIN number, you are required to update it, so that we can generate a GST Invoice.",
		]
	return None


@frappe.whitelist()
def get_site_request(product):
	team = frappe.local.team()
	requests = frappe.qb.get_query(
		"Product Trial Request",
		filters={
			"team": team.name,
			"product_trial": product,
		},
		fields=[
			"name",
			"status",
			"site",
			"site.trial_end_date as trial_end_date",
			"site.status as site_status",
			"site.plan as site_plan",
		],
		order_by="creation desc",
	).run(as_dict=1)
	if requests:
		site_request = requests[0]
		site_request.is_pending = (not site_request.site) or site_request.status in [
			"Pending",
			"Wait for Site",
			"Completing Setup Wizard",
			"Error",
		]
	else:
		site_request = frappe.new_doc(
			"Product Trial Request",
			product_trial=product,
			team=team.name,
		).insert(ignore_permissions=True)
		site_request.is_pending = True

	if hasattr(site_request, "site_plan") and site_request.site_plan:
		record = frappe.get_value(
			"Site Plan",
			site_request.site_plan,
			["is_trial_plan", "price_inr", "price_usd"],
			as_dict=1,
		)
		site_request.is_trial_plan = bool(
			frappe.get_value("Site Plan", site_request.site_plan, "is_trial_plan")
		)
		if team.currency == "INR":
			site_request.site_plan_description = f"₹{record.price_inr} / month"
		else:
			site_request.site_plan_description = f"${record.price_usd} / month"

	return site_request


def redirect_to(location):
	return build_response(
		frappe.local.request.path,
		"",
		301,
		{"Location": location, "Cache-Control": "no-store, no-cache, must-revalidate"},
	)


def get_frappe_io_auth_url() -> str | None:
	"""Get auth url for oauth login with frappe.io."""

	try:
		provider = frappe.get_last_doc(
			"Social Login Key", filters={"enable_social_login": 1, "provider_name": "Frappe"}
		)
	except DoesNotExistError:
		return None

	if (
		provider.base_url
		and provider.client_id
		and get_oauth_keys(provider.name)
		and provider.get_password("client_secret")
	):
		return get_oauth2_authorize_url(provider.name, redirect_to="")
	return None


@frappe.whitelist()
def get_emails():
	team = get_current_team(get_doc=True)
	return [
		{
			"type": "billing_email",
			"value": team.billing_email,
		},
		{
			"type": "notify_email",
			"value": team.notify_email,
		},
	]


@frappe.whitelist()
def update_emails(data):
	from frappe.utils import validate_email_address

	data = {x["type"]: x["value"] for x in json.loads(data)}
	for _key, value in data.items():
		validate_email_address(value, throw=True)

	team_doc = get_current_team(get_doc=True)

	team_doc.billing_email = data["billing_email"]
	team_doc.notify_email = data["notify_email"]

	team_doc.save()


@frappe.whitelist()
def add_key(key):
	frappe.get_doc({"doctype": "User SSH Key", "user": frappe.session.user, "ssh_public_key": key}).insert()


@frappe.whitelist()
def mark_key_as_default(key_name):
	key = frappe.get_doc("User SSH Key", key_name)
	key.is_default = True
	key.save()


@frappe.whitelist()
def create_api_secret():
	user = frappe.get_doc("User", frappe.session.user)

	api_key = user.api_key
	api_secret = frappe.generate_hash()

	if not api_key:
		api_key = frappe.generate_hash()
		user.api_key = api_key

	user.api_secret = api_secret
	user.save(ignore_permissions=True)

	return {"api_key": api_key, "api_secret": api_secret}


@frappe.whitelist()
def me():
	return {"user": frappe.session.user, "team": get_current_team()}


@frappe.whitelist()
def fuse_list():
	team = get_current_team(get_doc=True)
	query = f"""
		SELECT
			'Site' as doctype, name as title, name as route
		FROM
			`tabSite`
		WHERE
			team = '{team.name}' AND status NOT IN ('Archived')
		UNION ALL
		SELECT 'Bench' as doctype, title as title, name as route
		FROM
			`tabRelease Group`
		WHERE
			team = '{team.name}' AND enabled = 1
		UNION ALL
		SELECT 'Server' as doctype, name as title, name as route
		FROM
			`tabServer`
		WHERE
			team = '{team.name}' AND status = 'Active'
	"""

	return frappe.db.sql(query, as_dict=True)


# Permissions
@frappe.whitelist()
def get_permission_options(name, ptype):
	"""
	[{'doctype': 'Site', 'name': 'ccc.frappe.cloud', title: '', 'perms': 'press.api.site.get'}, ...]
	"""
	from press.press.doctype.press_method_permission.press_method_permission import (
		available_actions,
	)

	doctypes = frappe.get_all("Press Method Permission", pluck="document_type", distinct=True)

	options = []
	for doctype in doctypes:
		doc = frappe.qb.DocType(doctype)
		perm_doc = frappe.qb.DocType("Press User Permission")
		subtable = (
			frappe.qb.from_(perm_doc)
			.select("*")
			.where((perm_doc.user if ptype == "user" else perm_doc.group) == name)
		)

		query = (
			frappe.qb.from_(doc)
			.left_join(subtable)
			.on(doc.name == subtable.document_name)
			.select(
				ValueWrapper(doctype, alias="doctype"),
				doc.name,
				doc.title if doctype != "Site" else None,
				GROUP_CONCAT(subtable.action, alias="perms"),
			)
			.where(
				(doc.team == get_current_team())
				& ((doc.enabled == 1) if doctype == "Release Group" else (doc.status != "Archived"))
			)
			.groupby(doc.name)
		)
		options += query.run(as_dict=True)

	return {"options": options, "actions": available_actions()}


@frappe.whitelist()
def update_permissions(user, ptype, updated):
	values = []
	drop = []

	for doctype, docs in updated.items():
		for doc, updated_perms in docs.items():
			ptype_cap = ptype.capitalize()
			old_perms = frappe.get_all(
				"Press User Permission",
				filters={
					"type": ptype_cap,
					ptype: user,
					"document_type": doctype,
					"document_name": doc,
				},
				pluck="action",
			)
			# perms to insert
			add = set(updated_perms).difference(set(old_perms))
			values += [(frappe.generate_hash(4), ptype_cap, doctype, doc, user, a) for a in add]

			# perms to remove
			remove = set(old_perms).difference(set(updated_perms))
			drop += frappe.get_all(
				"Press User Permission",
				filters={
					"type": ptype_cap,
					ptype: user,
					"document_type": doctype,
					"document_name": doc,
					"action": ("in", remove),
				},
				pluck="name",
			)

	if values:
		frappe.db.bulk_insert(
			"Press User Permission",
			fields=["name", "type", "document_type", "document_name", ptype, "action"],
			values=set(values),
			ignore_duplicates=True,
		)
	if drop:
		frappe.db.delete("Press User Permission", {"name": ("in", drop)})
	frappe.db.commit()


@frappe.whitelist()
def groups():
	return frappe.get_all("Press Permission Group", {"team": get_current_team()}, ["name", "title"])


@frappe.whitelist()
def permission_group_users(name):
	if get_current_team() != frappe.db.get_value("Press Permission Group", name, "team"):
		frappe.throw("You are not allowed to view this group")

	return frappe.get_all("Press Permission Group User", {"parent": name}, pluck="user")


@frappe.whitelist()
def add_permission_group(title):
	doc = frappe.get_doc(
		{"doctype": "Press Permission Group", "team": get_current_team(), "title": title}
	).insert(ignore_permissions=True)
	return {"name": doc.name, "title": doc.title}


@frappe.whitelist()
@protected("Press Permission Group")
def remove_permission_group(name):
	frappe.db.delete("Press User Permission", {"group": name})
	frappe.delete_doc("Press Permission Group", name)


@frappe.whitelist()
@protected("Press Permission Group")
def add_permission_group_user(name, user):
	doc = frappe.get_doc("Press Permission Group", name)
	doc.append("users", {"user": user})
	doc.save(ignore_permissions=True)


@frappe.whitelist()
@protected("Press Permission Group")
def remove_permission_group_user(name, user):
	doc = frappe.get_doc("Press Permission Group", name)
	for group_user in doc.users:
		if group_user.user == user:
			doc.remove(group_user)
			doc.save(ignore_permissions=True)
			break


@frappe.whitelist()
def get_permission_roles():
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleUser = frappe.qb.DocType("Press Role User")

	return (
		frappe.qb.from_(PressRole)
		.select(
			PressRole.name,
			PressRole.admin_access,
			PressRole.allow_billing,
			PressRole.allow_apps,
			PressRole.allow_partner,
			PressRole.allow_site_creation,
			PressRole.allow_bench_creation,
			PressRole.allow_server_creation,
			PressRole.allow_webhook_configuration,
		)
		.join(PressRoleUser)
		.on((PressRole.name == PressRoleUser.parent) & (PressRoleUser.user == frappe.session.user))
		.where(PressRole.team == get_current_team())
		.run(as_dict=True)
	)


@frappe.whitelist()
def get_user_ssh_keys():
	return frappe.db.get_list(
		"User SSH Key",
		{"is_removed": 0, "user": frappe.session.user},
		["name", "ssh_fingerprint", "creation", "is_default"],
		order_by="creation desc",
	)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def is_2fa_enabled(user):
	return frappe.db.get_value("User 2FA", user, "enabled")


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def verify_2fa(user, totp_code):
	user_totp_secret = get_decrypted_password("User 2FA", user, "totp_secret")
	verified = pyotp.TOTP(user_totp_secret).verify(totp_code)

	if not verified:
		frappe.throw("Invalid 2FA code", frappe.AuthenticationError)

	return verified


@frappe.whitelist()
def get_2fa_qr_code_url():
	"""Get the QR code URL for 2FA provisioning"""

	if frappe.db.exists("User 2FA", frappe.session.user):
		user_totp_secret = get_decrypted_password("User 2FA", frappe.session.user, "totp_secret")
	else:
		user_totp_secret = pyotp.random_base32()
		frappe.get_doc(
			{
				"doctype": "User 2FA",
				"user": frappe.session.user,
				"totp_secret": user_totp_secret,
			}
		).insert()

	return pyotp.totp.TOTP(user_totp_secret).provisioning_uri(
		name=frappe.session.user, issuer_name="Frappe Cloud"
	)


@frappe.whitelist()
def enable_2fa(totp_code):
	"""Enable 2FA for the user after verifying the TOTP code"""

	if frappe.db.exists("User 2FA", frappe.session.user):
		user_totp_secret = get_decrypted_password("User 2FA", frappe.session.user, "totp_secret")
	else:
		frappe.throw(f"2FA is not enabled for {frappe.session.user}")

	if pyotp.totp.TOTP(user_totp_secret).verify(totp_code):
		frappe.db.set_value("User 2FA", frappe.session.user, "enabled", 1)
	else:
		frappe.throw("Invalid TOTP code")


@frappe.whitelist()
def disable_2fa(totp_code):
	"""Disable 2FA for the user after verifying the TOTP code"""

	if frappe.db.exists("User 2FA", frappe.session.user):
		user_totp_secret = get_decrypted_password("User 2FA", frappe.session.user, "totp_secret")
	else:
		frappe.throw(f"2FA is not enabled for {frappe.session.user}")

	if pyotp.totp.TOTP(user_totp_secret).verify(totp_code):
		frappe.db.set_value("User 2FA", frappe.session.user, "enabled", 0)
	else:
		frappe.throw("Invalid TOTP code")
