# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from press.utils import log_error


@frappe.whitelist()
def new(name):
	app = frappe.get_doc({"doctype": "Frappe App", "name": name})
	app.insert()
	return app


@frappe.whitelist()
def all():
	groups = frappe.get_all("Release Group", filters={"owner": frappe.session.user})
	if groups:
		group = groups[0]
		group = frappe.get_doc("Release Group", group.name)
		return group
	else:
		return []


@frappe.whitelist(allow_guest=True)
def hook(*args, **kwargs):
	event = frappe.request.headers.get("X-Github-Event")

	if event != "push":
		return

	payload = frappe.request.get_data()
	try:
		payload = json.loads(payload)

		url = payload["repository"]["html_url"]
		branch = payload["ref"].rsplit("refs/heads/")[1]

		app = frappe.get_all("Frappe App", {"url": url, "branch": branch})[0].name

		hash = payload["after"]
		if not frappe.db.exists("App Release", {"app": app, "hash": hash}):
			frappe.get_doc({"doctype": "App Release", "app": app, "hash": hash}).insert(
				ignore_permissions=True
			)

	except Exception:
		log_error("GitHub Webhook Error", payload=payload)
