# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.handler import is_whitelisted


@frappe.whitelist(allow_guest=True)
def upload_file():
	if frappe.session.user == "Guest":
		return

	files = frappe.request.files
	is_private = frappe.form_dict.is_private
	doctype = frappe.form_dict.doctype
	docname = frappe.form_dict.docname
	fieldname = frappe.form_dict.fieldname
	file_url = frappe.form_dict.file_url
	folder = frappe.form_dict.folder or "Home"
	method = frappe.form_dict.method
	content = None
	filename = None

	if "file" in files:
		file = files["file"]
		content = file.stream.read()
		filename = file.filename

	frappe.local.uploaded_file = content
	frappe.local.uploaded_filename = filename

	if method:
		method = frappe.get_attr(method)
		is_whitelisted(method)
		return method()
	else:
		ret = frappe.get_doc(
			{
				"doctype": "File",
				"attached_to_doctype": doctype,
				"attached_to_name": docname,
				"attached_to_field": fieldname,
				"folder": folder,
				"file_name": filename,
				"file_url": file_url,
				"is_private": cint(is_private),
				"content": content,
			}
		)
		ret.save()
		return ret


def on_session_creation():
	from press.utils import get_default_team_for_user

	onboarding_complete = frappe.cache().hget("onboarding_complete", frappe.session.user)
	if not onboarding_complete:
		team = get_default_team_for_user(frappe.session.user)
		onboarding = frappe.get_doc("Team", team).get_onboarding()
		onboarding_complete = onboarding["complete"]

		if onboarding_complete:
			# cache if onboarding is complete
			frappe.cache().hset("onboarding_complete", frappe.session.user, True)

	route = "/sites" if onboarding_complete else "/welcome"
	frappe.local.response.update({"dashboard_route": route})
