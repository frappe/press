# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.password import get_decrypted_password


@frappe.whitelist()
def new(site):
	server = frappe.get_all("Server", limit=1)[0].name
	bench = frappe.get_all("Bench", filters={"server": server}, limit=1)[0].name
	site = frappe.get_doc(
		{
			"doctype": "Site",
			"name": site["name"],
			"server": server,
			"bench": bench,
			"apps": [{"app": app} for app in site["apps"]],
		},
	).insert(ignore_permissions=True)
	return {
		"name": site.name,
		"password": get_decrypted_password("Site", site.name, "password"),
	}


@frappe.whitelist()
def available():
	bench = frappe.get_all("Bench", limit=1)[0].name
	apps = frappe.get_all(
		"Installed App", fields=["app"], filters={"parent": bench}, order_by="idx"
	)
	return {"name": bench, "apps": [app.app for app in apps]}


@frappe.whitelist()
def all():
	sites = frappe.get_all(
		"Site", fields=["name", "status"], filters={"owner": frappe.session.user}
	)
	return sites


@frappe.whitelist()
def get(name):
	site = frappe.get_doc("Site", name)
	apps = [app.app for app in site.apps]
	apps = frappe.get_all("Frappe App", fields=["name", "repo_owner as owner", "scrubbed as repo", "url", "branch"], filters={"name": ("in", apps)})
	return {
		"name": site.name,
		"status": site.status,
		"installed_apps": apps,
		"creation": site.creation,
		"last_updated": site.modified,
	}


@frappe.whitelist()
def analytics(name):
	requests_per_minute = frappe.db.sql("""SELECT COUNT(*) AS value, timestamp FROM `tabSite Request Log` WHERE site = %s GROUP BY EXTRACT(DAY_MINUTE FROM timestamp)""", name, as_dict=True)
	request_cpu_time_per_minute = frappe.db.sql("""SELECT SUM(duration) AS value, timestamp FROM `tabSite Request Log` WHERE site = %s GROUP BY EXTRACT(DAY_MINUTE FROM timestamp)""", name, as_dict=True)
	
	jobs_per_minute = frappe.db.sql("""SELECT COUNT(*) AS value, timestamp FROM `tabSite Job Log` WHERE site = %s GROUP BY EXTRACT(DAY_MINUTE FROM timestamp)""", name, as_dict=True)
	job_cpu_time_per_minute = frappe.db.sql("""SELECT SUM(duration) AS value, timestamp FROM `tabSite Job Log` WHERE site = %s GROUP BY EXTRACT(DAY_MINUTE FROM timestamp)""", name, as_dict=True)

	return {
		"requests_per_minute": requests_per_minute,
		"request_cpu_time_per_minute": request_cpu_time_per_minute,
		"jobs_per_minute": jobs_per_minute,
		"job_cpu_time_per_minute": job_cpu_time_per_minute,
	}