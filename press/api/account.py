# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import frappe
import frappe.utils
import pyotp
from frappe import _
from frappe.core.doctype.user.user import update_password
from frappe.core.utils import find
from frappe.exceptions import DoesNotExistError
from frappe.query_builder.custom import GROUP_CONCAT
from frappe.query_builder.functions import Count
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_url
from frappe.utils.data import sha256_hash
from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
from frappe.utils.password import get_decrypted_password
from frappe.website.utils import build_response
from pypika.terms import ValueWrapper

from press.api.site import protected
from press.guards import mfa
from press.guards.role_guard import skip_roles
from press.press.doctype.team.team import (
	Team,
	get_child_team_members,
	get_team_members,
)
from press.utils import get_country_info, get_current_team, is_user_part_of_team, log_error
from press.utils.telemetry import capture

if TYPE_CHECKING:
	from press.press.doctype.account_request.account_request import AccountRequest
	from press.press.doctype.user_2fa_recovery_code import User2FARecoveryCode


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def signup(email: str, product: str | None = None, referrer: str | None = None) -> str:
	frappe.utils.validate_email_address(email, True)

	email = email.strip().lower()
	exists, enabled = frappe.db.get_value("Team", {"user": email}, ["name", "enabled"]) or [0, 0]

	account_request = None
	if exists and not enabled:
		frappe.throw(_("Account {0} has been deactivated").format(email))
	elif exists and enabled:
		frappe.throw(_("Account {0} is already registered").format(email))

	account_request = frappe.db.get_value(
		"Account Request",
		{
			"email": email,
			"referrer_id": referrer,
			"product_trial": product,
			"invited_by": ("is", "not set"),
		},
		"name",
	)

	if not account_request:
		account_request_doc = frappe.get_doc(
			{
				"doctype": "Account Request",
				"email": email,
				"role": "Press Admin",
				"referrer_id": referrer,
				"send_email": True,
				"product_trial": product,
				"agreed_to_terms": 1,
			}
		).insert(ignore_permissions=True)
		account_request = account_request_doc.name

	return account_request


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def verify_otp(account_request: str, otp: str) -> str:
	from frappe.auth import get_login_attempt_tracker

	account_request_doc: "AccountRequest" = frappe.get_doc("Account Request", account_request)
	ip_tracker = get_login_attempt_tracker(frappe.local.request_ip)

	# ensure no team has been created with this email
	if (
		frappe.db.exists("Team", {"user": account_request_doc.email})
		and not account_request_doc.product_trial
	):
		ip_tracker and ip_tracker.add_failure_attempt()
		frappe.throw("Invalid OTP. Please try again.")
	if account_request_doc.otp != otp:
		ip_tracker and ip_tracker.add_failure_attempt()
		frappe.throw("Invalid OTP. Please try again.")

	ip_tracker and ip_tracker.add_success_attempt()
	account_request_doc.reset_otp()

	if account_request_doc.product_trial:
		capture("otp_verified", "fc_product_trial", account_request_doc.name)

	return account_request_doc.request_key


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def verify_otp_and_login(email: str, otp: str):
	from frappe.auth import get_login_attempt_tracker

	account_request = frappe.db.get_value("Account Request", {"email": email}, "name")

	if not account_request:
		frappe.throw("Please sign up first")

	account_request_doc: "AccountRequest" = frappe.get_doc("Account Request", account_request)
	ip_tracker = get_login_attempt_tracker(frappe.local.request_ip)

	if account_request_doc.otp != otp:
		ip_tracker and ip_tracker.add_failure_attempt()
		frappe.throw("Invalid OTP. Please try again.")

	ip_tracker and ip_tracker.add_success_attempt()
	account_request_doc.reset_otp()

	return frappe.local.login_manager.login_as(email)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def resend_otp(account_request: str, for_2fa_keys: bool = False):
	account_request_doc: "AccountRequest" = frappe.get_doc("Account Request", account_request)

	# if last OTP was sent less than 30 seconds ago, throw an error
	if (
		account_request_doc.otp_generated_at
		and (frappe.utils.now_datetime() - account_request_doc.otp_generated_at).seconds < 30
	):
		frappe.throw("Please wait for 30 seconds before requesting a new OTP")

	# ensure no team has been created with this email
	if (
		frappe.db.exists("Team", {"user": account_request_doc.email})
		and not account_request_doc.product_trial
	):
		frappe.throw("Invalid Email")
	account_request_doc.reset_otp()
	account_request_doc.send_otp_mail(for_login=not for_2fa_keys)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def send_otp(email: str, for_2fa_keys: bool = False):
	account_request = frappe.db.get_value("Account Request", {"email": email}, "name")

	if not account_request:
		frappe.throw("Please sign up first")

	account_request_doc: "AccountRequest" = frappe.get_doc("Account Request", account_request)

	# if last OTP was sent less than 30 seconds ago, throw an error
	if (
		account_request_doc.otp_generated_at
		and (frappe.utils.now_datetime() - account_request_doc.otp_generated_at).seconds < 30
	):
		frappe.throw("Please wait for 30 seconds before requesting a new OTP")

	account_request_doc.reset_otp()
	account_request_doc.send_otp_mail(for_login=not for_2fa_keys)


@frappe.whitelist(allow_guest=True)
def setup_account(  # noqa: C901
	key,
	first_name=None,
	last_name=None,
	password=None,
	is_invitation=False,
	country=None,
	phone=None,
	user_exists=False,
	invited_by_parent_team=False,
	oauth_signup=False,
	oauth_domain=False,
	site_domain=None,
	share_details_consent=False,
):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	if not user_exists:
		if not first_name:
			frappe.throw("First Name is required")

		if not is_invitation and not country:
			frappe.throw("Country is required")

		if not is_invitation and country:
			all_countries = frappe.db.get_all("Country", pluck="name")
			country = find(all_countries, lambda x: x.lower() == country.lower())
			if not country:
				frappe.throw("Please provide a valid country name")

	# if the request is authenticated, set the user to Administrator
	frappe.set_user("Administrator")

	# pass lead to local partner if consent given
	account_request.agreed_to_partner_consent = share_details_consent
	account_request.save()

	team = account_request.team
	email = account_request.email
	role = account_request.role
	press_roles = account_request.press_roles

	if is_invitation:
		# if this is a request from an invitation
		# then Team already exists and will be added to that team
		doc = frappe.get_doc("Team", team)
		doc.create_user_for_member(
			first_name,
			last_name,
			email,
			password,
			role,
			press_roles,
			skip_validations=True,
		)
	else:
		# Team doesn't exist, create it
		Team.create_new(
			account_request=account_request,
			first_name=first_name,
			last_name=last_name,
			password=password,
			country=country,
			phone=phone,
			user_exists=bool(user_exists),
		)
		if invited_by_parent_team:
			doc = frappe.get_doc("Team", account_request.invited_by)
			doc.append("child_team_members", {"child_team": team})
			doc.save()

	# Telemetry: Created account
	if account_request.product_trial:
		capture("created_account", "fc_product_trial", account_request.name)
	else:
		capture("completed_signup", "fc_signup", account_request.email)
	frappe.local.login_manager.login_as(email)

	return account_request.name


@frappe.whitelist()
@rate_limit(limit=5, seconds=60 * 60)
def accept_team_invite(key: str):
	account_request = get_account_request_from_key(key)

	if not account_request:
		frappe.throw("Invalid or Expired Key")

	if not account_request.invited_by:
		frappe.throw("You are not invited by any team")

	team = account_request.team
	first_name = account_request.first_name
	last_name = account_request.last_name
	email = account_request.email
	password = None
	role = account_request.role
	press_roles = account_request.press_roles

	team_doc = frappe.get_doc("Team", team)
	return team_doc.create_user_for_member(first_name, last_name, email, password, role, press_roles)


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

	team.disable_account()


@frappe.whitelist()
def has_active_servers(team):
	return frappe.db.exists("Server", {"status": "Active", "team": team})


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
				f"The process for deletion of your team {team} has been initiated. Sorry to see you go :(",
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
			"product_trial": frappe.db.get_value(
				"Product Trial", account_request.product_trial, ["logo", "name"], as_dict=1
			),
		}

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


def get_account_request_from_key(key: str):
	"""Find Account Request using `key`"""

	if not key or not isinstance(key, str):
		frappe.throw(_("Invalid Key"))

	try:
		return frappe.get_doc("Account Request", {"request_key": key})
	except frappe.DoesNotExistError:
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
			["title", "logo"],
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
	STR_FORMAT = re.compile("^[a-zA-Z']+$")
	if (first_name and not STR_FORMAT.match(first_name)) or (last_name and not STR_FORMAT.match(last_name)):
		frappe.throw("Names cannot contain invalid characters")
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
@mfa.verify(user_key="email", raise_error=True)
def send_reset_password_email(email: str):
	"""
	Sends reset password email to the user.
	"""
	frappe.utils.validate_email_address(email, throw=True)

	# Abort if user does not exist.
	if not frappe.db.exists("User", email):
		return

	key = frappe.generate_hash()
	url = get_url("/dashboard/reset-password/" + key)
	frappe.db.set_value("User", email, "reset_password_key", sha256_hash(key))
	frappe.db.set_value("User", email, "last_reset_password_key_generated_on", frappe.utils.now_datetime())

	frappe.sendmail(
		recipients=email,
		subject="Reset Password",
		template="reset_password",
		args={
			"link": url,
		},
		now=True,
	)


@frappe.whitelist(allow_guest=True)
def reset_password(key, password):
	return update_password(new_password=password, key=key)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60)
def get_user_for_reset_password_key(key):
	if not key or not isinstance(key, str):
		frappe.throw(_("Invalid Key"))

	hashed_key = sha256_hash(key)
	user_doc = frappe.db.get_value(
		"User",
		{"reset_password_key": hashed_key},
		["name", "last_reset_password_key_generated_on"],
		as_dict=True,
	)
	if not user_doc:
		frappe.throw(_("Invalid Key"))

	from datetime import timedelta

	if user_doc.last_reset_password_key_generated_on:
		expiry_time = user_doc.last_reset_password_key_generated_on + timedelta(minutes=10)
		if frappe.utils.now_datetime() > expiry_time:
			frappe.throw(_("Key has expired. Please retry resetting your password."))

	return user_doc.name


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
	try:
		billing_details = frappe._dict(billing_details)
		team = get_current_team(get_doc=True)
		validate_pincode(billing_details)
		if (team.country != billing_details.country) and (
			team.country == "India" or billing_details.country == "India"
		):
			frappe.throw("Cannot change country after registration")
		team.update_billing_details(billing_details)
	except Exception as ex:
		log_error(
			"Billing update failing",
			data=ex,
			reference_doctype="Team",
		)


def validate_pincode(billing_details):
	# Taken from https://github.com/resilient-tech/india-compliance
	if billing_details.country != "India" or not billing_details.postal_code:
		return
	PINCODE_FORMAT = re.compile(r"^[1-9][0-9]{5}$")
	if not PINCODE_FORMAT.match(billing_details.postal_code):
		frappe.throw("Invalid Postal Code")

	if billing_details.state not in STATE_PINCODE_MAPPING:
		return

	first_three_digits = cint(billing_details.postal_code[:3])
	postal_code_range = STATE_PINCODE_MAPPING[billing_details.state]

	if isinstance(postal_code_range[0], int):
		postal_code_range = (postal_code_range,)

	for lower_limit, upper_limit in postal_code_range:
		if lower_limit <= int(first_three_digits) <= upper_limit:
			return

	frappe.throw(f"Postal Code {billing_details.postal_code} is not associated with {billing_details.state}")


@frappe.whitelist(allow_guest=True)
def feedback(team, message, note, rating, route=None):
	feedback = frappe.new_doc("Press Feedback")
	team_doc = frappe.get_doc("Team", team)
	feedback.team = team
	feedback.message = message
	feedback.note = note
	feedback.route = route
	feedback.rating = rating / 5
	feedback.team_created_on = frappe.utils.getdate(team_doc.creation)
	feedback.currency = team_doc.currency
	invs = frappe.get_all(
		"Invoice",
		{"team": team, "status": "Paid", "type": "Subscription"},
		pluck="total",
		order_by="creation desc",
		limit=1,
	)
	feedback.last_paid_invoice = 0 if not invs else invs[0]
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
	team = get_current_team(get_doc=False)
	return frappe.get_all(
		"Communication Info",
		filters={
			"parent": team,
			"parenttype": "Team",
			"parentfield": "emails",
		},
		fields=["channel", "type", "value"],
	)


@frappe.whitelist()
def update_emails(data):
	from frappe.utils import validate_email_address

	data = {x["type"]: x["value"] for x in json.loads(data)}
	for _key, value in data.items():
		validate_email_address(value, throw=True)

	team_doc = get_current_team(get_doc=True)

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


def has_user_permission(key: str):
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleUser = frappe.qb.DocType("Press Role User")
	return (
		frappe.qb.from_(PressRole)
		.inner_join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.select(Count(PressRole.name).as_("count"))
		.where(PressRole.team == get_current_team())
		.where(PressRole[key] == 1)
		.where(PressRoleUser.user == frappe.session.user)
		.run(as_dict=True)
		.pop()
		.get("count")
		> 0
	)


@frappe.whitelist()
def user_permissions():
	team = get_current_team(get_doc=True)
	is_owner = team.user == frappe.session.user
	is_admin = is_owner or skip_roles() or has_user_permission("admin_access")
	return {
		"owner": is_owner,
		"admin": is_admin,
		"billing": is_admin or has_user_permission("allow_billing"),
		"webhook": is_admin or has_user_permission("allow_webhook_configuration"),
		"apps": is_admin or has_user_permission("allow_apps"),
		"partner": is_admin or has_user_permission("allow_partner"),
		"partner_dashboard": is_admin or has_user_permission("allow_dashboard"),
		"partner_leads": is_admin or has_user_permission("allow_leads"),
		"partner_customer": is_admin or has_user_permission("allow_customer"),
		"partner_contribution": is_admin or has_user_permission("allow_contribution"),
		"site_creation": is_admin or has_user_permission("allow_site_creation"),
		"bench_creation": is_admin or has_user_permission("allow_bench_creation"),
		"server_creation": is_admin or has_user_permission("allow_server_creation"),
	}


@frappe.whitelist()
def get_user_ssh_keys():
	return frappe.db.get_list(
		"User SSH Key",
		{"is_removed": 0, "user": frappe.session.user},
		["name", "ssh_fingerprint", "creation", "is_default"],
		order_by="creation desc",
	)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=20, seconds=60 * 60)
def is_2fa_enabled(user: str) -> bool:
	return bool(frappe.db.get_value("User 2FA", user, "enabled"))


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def verify_2fa(user, totp_code):
	user_totp_secret = get_decrypted_password("User 2FA", user, "totp_secret")
	verified = pyotp.TOTP(user_totp_secret).verify(totp_code)

	if verified:
		frappe.db.set_value("User 2FA", user, "last_verified_at", frappe.utils.now())
	else:
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

	two_fa = frappe.get_doc("User 2FA", frappe.session.user)

	user_totp_secret = get_decrypted_password("User 2FA", frappe.session.user, "totp_secret")

	if not pyotp.totp.TOTP(user_totp_secret).verify(totp_code):
		frappe.throw("Invalid TOTP code")

	two_fa.enabled = 1

	if not two_fa.recovery_codes:
		for recovery_code in two_fa.generate_recovery_codes():
			two_fa.append(
				"recovery_codes",
				{"code": recovery_code},
			)

	two_fa.mark_recovery_codes_viewed()
	two_fa.save()

	try:
		from frappe.sessions import clear_sessions

		clear_sessions(keep_current=True)
	except Exception as e:
		log_error(
			"2FA Enable: Failed clearing other sessions",
			data=e,
			reference_doctype="User 2FA",
			reference_name=two_fa.name,
		)

	return [
		get_decrypted_password("User 2FA Recovery Code", recovery_code.name, "code")
		for recovery_code in two_fa.recovery_codes
		if not recovery_code.used_at
	]


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


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60 * 60)
def recover_2fa(user: str, recovery_code: str):
	"""Recover 2FA using a recovery code."""
	# Get the User 2FA document.
	two_fa = frappe.get_doc("User 2FA", user)

	# Check if the user has 2FA enabled.
	if not two_fa.enabled:
		frappe.throw(f"2FA is not enabled for {user}")

	# Get valid recovery code doc.
	code: "User2FARecoveryCode" | None = None
	for code_doc in two_fa.recovery_codes:
		decrypted_code = get_decrypted_password("User 2FA Recovery Code", code_doc.name, "code")
		if decrypted_code == recovery_code and not code_doc.used_at:
			code = code_doc
			break

	# If no valid recovery code found, throw an error.
	if not code:
		frappe.throw("Invalid or used recovery code")
	assert code is not None
	# Mark the recovery code as used.
	code.used_at = frappe.utils.now_datetime()

	# Disable 2FA and save the document.
	two_fa.enabled = 0
	two_fa.save(ignore_permissions=True)


@frappe.whitelist()
def get_2fa_recovery_codes(verification_code: int):
	"""Get the recovery codes for the user."""

	if not frappe.db.exists("User 2FA", {"user": frappe.session.user, "enabled": 1}):
		frappe.throw("2FA is not enabled for this user")

	account_request: "AccountRequest" = frappe.get_doc("Account Request", {"email": frappe.session.user})

	if account_request.otp != verification_code:
		frappe.throw("Invalid OTP. Please try again.")

	account_request.reset_otp()

	# Get the User 2FA document.
	two_fa = frappe.get_doc("User 2FA", frappe.session.user)

	# Decrypt recovery codes for the user.
	recovery_codes = [
		get_decrypted_password("User 2FA Recovery Code", recovery_code.name, "code")
		for recovery_code in two_fa.recovery_codes
		if not recovery_code.used_at
	]

	# Add a timestamp for when the recovery codes were last viewed.
	two_fa.mark_recovery_codes_viewed()
	two_fa.save()

	# Return the recovery codes.
	return recovery_codes


@frappe.whitelist()
def reset_2fa_recovery_codes():
	"""Reset the recovery codes for the user."""

	# Check if the user has 2FA enabled.
	if not frappe.db.exists("User 2FA", frappe.session.user):
		frappe.throw("2FA is not enabled for this user")

	# Get the User 2FA document.
	two_fa = frappe.get_doc("User 2FA", frappe.session.user)

	# Clear existing recovery codes.
	two_fa.recovery_codes = []
	recovery_codes = list(two_fa.generate_recovery_codes())

	# Add new recovery codes.
	for recovery_code in recovery_codes:
		two_fa.append(
			"recovery_codes",
			{"code": recovery_code},
		)

	# Update time and save the document.
	two_fa.mark_recovery_codes_viewed()
	two_fa.save()

	# Return the new recovery codes.
	return recovery_codes


@frappe.whitelist()
def get_user_banners():
	team = get_current_team()

	# fetch sites + servers for this team
	site_server_pairs = frappe.get_all(
		"Site",
		filters={"team": team},
		fields=["name", "server"],
	)

	sites = list(set([pair["name"] for pair in site_server_pairs]))
	servers = list(set([pair["server"] for pair in site_server_pairs if pair.get("server")]))

	DashboardBanner = frappe.qb.DocType("Dashboard Banner")
	now = frappe.utils.now()

	# fetch all enabled banners for this user
	all_enabled_banners = (
		frappe.qb.from_(DashboardBanner)
		.select("*")
		.where(
			((DashboardBanner.enabled == 1) & (DashboardBanner.is_scheduled == 0))
			| (
				(DashboardBanner.enabled == 1)
				& (DashboardBanner.is_scheduled == 1)
				& (DashboardBanner.scheduled_start_time <= now)
				& (DashboardBanner.scheduled_end_time >= now)
			)
		)
		.where(
			(DashboardBanner.is_global == 1)
			| ((DashboardBanner.type_of_scope == "Site") & (DashboardBanner.site.isin(sites or [""])))
			| ((DashboardBanner.type_of_scope == "Server") & (DashboardBanner.server.isin(servers or [""])))
			| ((DashboardBanner.type_of_scope == "Team") & (DashboardBanner.team == team))
		)
		.run(as_dict=True)
	)

	# filter out dismissed banners
	banner_dismissals_by_user = frappe.get_all(
		"Dashboard Banner Dismissal",
		filters={"user": frappe.session.user, "parent": ["in", [b["name"] for b in all_enabled_banners]]},
		fields=["parent"],
		pluck=True,
	)

	# visible banners
	return [banner for banner in all_enabled_banners if banner["name"] not in banner_dismissals_by_user]


@frappe.whitelist()
def dismiss_banner(banner_name):
	user = frappe.session.user
	banner = frappe.get_doc("Dashboard Banner", banner_name)
	if banner and banner.is_dismissible and not banner.is_global:
		banner.append(
			"user_dismissals",
			{
				"user": user,
				"dismissed_at": frappe.utils.now(),
				"parent": banner_name,
			},
		)
		banner.save()
		return True
	return False


# Not available for Telangana, Ladakh, and Other Territory
STATE_PINCODE_MAPPING = {
	"Jammu and Kashmir": (180, 194),
	"Himachal Pradesh": (171, 177),
	"Punjab": (140, 160),
	"Chandigarh": ((140, 140), (160, 160)),
	"Uttarakhand": (244, 263),
	"Haryana": (121, 136),
	"Delhi": (110, 110),
	"Rajasthan": (301, 345),
	"Uttar Pradesh": (201, 285),
	"Bihar": (800, 855),
	"Sikkim": (737, 737),
	"Arunachal Pradesh": (790, 792),
	"Nagaland": (797, 798),
	"Manipur": (795, 795),
	"Mizoram": (796, 796),
	"Tripura": (799, 799),
	"Meghalaya": (793, 794),
	"Assam": (781, 788),
	"West Bengal": (700, 743),
	"Jharkhand": (813, 835),
	"Odisha": (751, 770),
	"Chhattisgarh": (490, 497),
	"Madhya Pradesh": (450, 488),
	"Gujarat": (360, 396),
	"Dadra and Nagar Haveli and Daman and Diu": ((362, 362), (396, 396)),
	"Maharashtra": (400, 445),
	"Karnataka": (560, 591),
	"Goa": (403, 403),
	"Lakshadweep Islands": (682, 682),
	"Kerala": (670, 695),
	"Tamil Nadu": (600, 643),
	"Puducherry": ((533, 533), (605, 605), (607, 607), (609, 609), (673, 673)),
	"Andaman and Nicobar Islands": (744, 744),
	"Andhra Pradesh": (500, 535),
}
