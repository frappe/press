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
from datetime import datetime, timedelta


@frappe.whitelist(allow_guest=True)
def signup(email):
	current_user = frappe.session.user
	frappe.set_user("Administrator")

	email = email.strip()
	exists, enabled = frappe.db.get_values("Team", email, ["name", "enabled"]) or [0, 0]

	if exists and not enabled:
		# account was created but not verified
		doc = frappe.get_doc("Team", email)
		doc.add_team_member(email, owner=True)
	elif exists and enabled:
		# account exists
		frappe.throw(_("Account {0} is already registered").format(email))
	else:
		doc = frappe.new_doc("Team")
		doc.name = email
		doc.add_team_member(email, owner=True)
		doc.insert()

	frappe.set_user(current_user)


@frappe.whitelist(allow_guest=True)
def setup_account(key, first_name=None, last_name=None, password=None):
	account_request = get_account_request_from_key(key)
	if not account_request:
		frappe.throw("Invalid or Expired Key")

	team = account_request.team
	email = account_request.email
	role = account_request.role

	doc = frappe.get_doc("Team", team)
	doc.create_user_for_member(first_name, last_name, email, password, role)

	frappe.local.login_manager.login_as(email)


@frappe.whitelist(allow_guest=True)
def get_email_from_request_key(key):
	account_request = get_account_request_from_key(key)
	if account_request:
		return {
			"email": account_request.email,
			"user_exists": frappe.db.exists("User", account_request.email),
			"team": account_request.team,
			"is_invitation": frappe.db.get_value("Team", account_request.team, "enabled"),
		}


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
def get(team=None):
	user = frappe.session.user
	team = team or user
	if frappe.db.exists("User", user):
		teams = [
			d.parent for d in frappe.db.get_all("Team Member", {"user": user}, ["parent"])
		]
		teams = list(set(teams))
		return {
			"user": frappe.get_doc("User", user),
			"team": frappe.get_doc("Team", team),
			"team_members": get_team_members(team),
			"teams": teams,
		}
	else:
		frappe.throw(_("Account does not exist"))


@frappe.whitelist()
def update_profile(first_name, last_name, email):
	user = frappe.session.user
	doc = frappe.get_doc("User", user)
	doc.first_name = first_name
	doc.last_name = last_name
	doc.email = email
	doc.save()
	return doc


@frappe.whitelist()
def update_profile_picture(image_url):
	user = frappe.get_doc("User", frappe.session.user)
	user.user_image = image_url
	user.save()


@frappe.whitelist(allow_guest=True)
def send_reset_password_email(email):
	email = email.strip()
	key = random_string(32)
	frappe.db.set_value("User", email, "reset_password_key", key)
	url = get_url("/dashboard/#/reset-password/" + key)
	frappe.sendmail(
		recipients=email,
		subject="Reset Password",
		template="reset_password",
		args={"link": url},
		now=True,
	)


@frappe.whitelist(allow_guest=True)
def reset_password(key, password):
	return update_password(new_password=password, key=key)


@frappe.whitelist(allow_guest=True)
def get_user_for_reset_password_key(key):
	return frappe.db.get_value("User", {"reset_password_key": key}, "name")


@frappe.whitelist()
def add_team_member(team, email):
	team_doc = frappe.get_doc("Team", team)
	if team_doc.user == frappe.session.user:
		team_doc.add_team_member(email)
	else:
		frappe.throw(_("Only Team Owner can add other members"), frappe.PermissionError)


@frappe.whitelist()
def switch_team(team):
	if frappe.db.exists("Team Member", {"parent": team, "user": frappe.session.user}):
		return {
			"team": frappe.get_doc("Team", team),
			"team_members": get_team_members(team),
		}


def redirect_to(location):
	return build_response(
		frappe.local.request.path,
		"",
		301,
		{"Location": location, "Cache-Control": "no-store, no-cache, must-revalidate"},
	)
