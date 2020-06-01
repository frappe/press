# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from press.utils import get_current_team


@frappe.whitelist()
def new(installation, url, owner, repo, branch, app_name, enable_auto_deploy):
	team = get_current_team()
	app = frappe.get_doc(
		{
			"doctype": "Frappe App",
			"name": f"{owner}/{repo}",
			"branch": branch,
			"url": url,
			"repo": repo,
			"repo_owner": owner,
			"scrubbed": app_name,
			"installation": installation,
			"team": team,
			"enable_auto_deploy": enable_auto_deploy,
		}
	)
	app.insert()
	return app.name


@frappe.whitelist()
def get(name):
	app = frappe.get_doc("Frappe App", name)
	return {"name": app.name, "url": app.url, "releases": [], "deploys": []}


@frappe.whitelist()
def all():
	if frappe.session.data.user_type == "System User":
		filters = {}
	else:
		filters = {"team": get_current_team()}
	apps = frappe.get_list(
		"Frappe App",
		fields=["name", "modified", "url", "branch"],
		filters=filters,
		order_by="creation desc",
	)

	return apps
