# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def signup(first_name, last_name, email):
	try:
		doc = frappe.new_doc("User Account")
		doc.first_name = first_name
		doc.last_name = last_name
		doc.email = email
		doc.name = email
		doc.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		frappe.clear_last_message()
		frappe.throw(_("Account {0} is already registered").format(email))


@frappe.whitelist()
def get():
	try:
		user = frappe.session.user
		if user == 'Administrator':
			doc = frappe.new_doc('User Account')
			doc.first_name = 'Administrator'
		else:
			doc = frappe.get_doc('User Account', user)

		out = doc.as_dict()
		out.image = frappe.db.get_value('User', user, 'user_image')
		return out
	except frappe.DoesNotExistError:
		frappe.throw(_('Account does not exist'))

@frappe.whitelist()
def update_profile(first_name, last_name, email):
	user = frappe.session.user
	doc = frappe.get_doc('User Account', user)
	doc.first_name = first_name
	doc.last_name = last_name
	doc.email = email
	doc.save()
	return doc

@frappe.whitelist()
def update_profile_picture(image_url):
	user = frappe.get_doc('User', frappe.session.user)
	user.user_image = image_url
	user.save()
