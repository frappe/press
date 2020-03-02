# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import random_string, get_url
from frappe.utils.verified_command import verify_request
from frappe.website.render import build_response
from frappe.core.doctype.user.user import update_password


@frappe.whitelist(allow_guest=True)
def signup(first_name, last_name, email):
	first_name = first_name.strip()
	last_name = last_name.strip()
	email = email.strip()
	try:
		doc = frappe.new_doc("User Account")
		doc.first_name = first_name
		doc.last_name = last_name
		doc.email = email
		doc.name = email
		doc.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		frappe.clear_last_message()
		if frappe.db.exists("User", email):
			# account exists
			frappe.throw(_("Account {0} is already registered").format(email))
		else:
			# account was created but not verified
			doc = frappe.get_doc("User Account", email)
			doc.first_name = first_name
			doc.last_name = last_name
			doc.save(ignore_permissions=True)
			doc.send_verification_email()


@frappe.whitelist(allow_guest=True)
def verify_account(user):
	if not verify_request():
		frappe.throw("Invalid or expired link")

	# set account key
	doc = frappe.get_doc("User Account", user)
	key = random_string(32)
	doc.db_set("account_key", key)
	frappe.db.commit()

	return redirect_to(get_url("/dashboard/#/setup-account/" + key))


@frappe.whitelist(allow_guest=True)
def setup_account(key, password):
	user_account = get_user_for_key(key)
	if user_account:
		doc = frappe.get_doc("User Account", user_account)
		doc.create_user(password)
		frappe.local.login_manager.login_as(user_account)
	else:
		frappe.throw("Invalid Account Key")


@frappe.whitelist(allow_guest=True)
def get_user_for_key(key):
	return frappe.db.get_value("User Account", {"account_key": key}, "name")


@frappe.whitelist()
def get():
	try:
		user = frappe.session.user
		if user == "Administrator":
			doc = frappe.new_doc("User Account")
			doc.first_name = "Administrator"
		else:
			doc = frappe.get_doc("User Account", user)

		out = doc.as_dict()
		out.image = frappe.db.get_value("User", user, "user_image")
		return out
	except frappe.DoesNotExistError:
		frappe.throw(_("Account does not exist"))


@frappe.whitelist()
def update_profile(first_name, last_name, email):
	user = frappe.session.user
	doc = frappe.get_doc("User Account", user)
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
	user = frappe.get_doc("User Account", email)
	user.send_reset_password_email()
	return True


@frappe.whitelist(allow_guest=True)
def reset_password(key, password):
	return update_password(new_password=password, key=key)


@frappe.whitelist(allow_guest=True)
def get_user_for_reset_password_key(key):
	return frappe.db.get_value("User", {"reset_password_key": key}, "name")


def redirect_to(location):
	return build_response(
		frappe.local.request.path,
		"",
		301,
		{"Location": location, "Cache-Control": "no-store, no-cache, must-revalidate",},
	)
