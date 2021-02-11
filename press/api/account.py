# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import random_string, get_url
from frappe.website.render import build_response
from frappe.core.doctype.user.user import update_password
from press.press.doctype.team.team import get_team_members
from press.utils import get_country_info, get_current_team
from datetime import datetime, timedelta


@frappe.whitelist(allow_guest=True)
def signup(email):
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
			{"doctype": "Account Request", "email": email, "role": "Press Admin"}
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
		doc = frappe.get_doc(
			{"doctype": "Team", "name": team, "user": email, "country": country, "enabled": 1}
		)
		doc.insert(ignore_permissions=True, ignore_links=True)
		doc.create_user_for_member(first_name, last_name, email, password, role)
		doc.create_stripe_customer()
		doc.create_upcoming_invoice()

		if doc.has_partner_account_on_erpnext_com():
			doc.enable_erpnext_partner_privileges()

	frappe.local.login_manager.login_as(email)


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
	"""Find Account Request using `key` in the past 30 minutes"""
	minutes = 30
	result = frappe.db.get_all(
		"Account Request",
		filters={
			"request_key": key,
			"creation": (">", datetime.now() - timedelta(seconds=minutes * 60)),
		},
		fields=["name", "email", "team", "role"],
		order_by="creation desc",
		limit=1,
	)
	if result:
		return result[0]


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
	teams = list(set(teams))
	return {
		"user": frappe.get_doc("User", user),
		"team": team_doc,
		"team_members": get_team_members(team),
		"teams": teams,
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
		url = get_url("/dashboard/#/reset-password/" + key)
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
def add_team_member(team, email):
	frappe.utils.validate_email_address(email, True)

	team_doc = frappe.get_doc("Team", team)
	if team_doc.user != frappe.session.user:
		frappe.throw(_("Only Team Owner can add other members"), frappe.PermissionError)

	frappe.get_doc(
		{
			"doctype": "Account Request",
			"team": team,
			"email": email,
			"role": "Press Member",
			"invited_by": team_doc.user,
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
def onboarding():
	team = get_current_team()
	return frappe.get_doc("Team", team).get_onboarding()


@frappe.whitelist()
def skip_onboarding_step(step_name):
	team = get_current_team(True)
	team.update_onboarding(step_name, "Skipped")


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
