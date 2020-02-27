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
	apps = frappe.get_all(
		"Frappe App",
		fields=["name", "repo_owner as owner", "scrubbed as repo", "url", "branch"],
		filters={"name": ("in", apps)},
	)
	return {
		"name": site.name,
		"status": site.status,
		"installed_apps": apps,
		"creation": site.creation,
		"last_updated": site.modified,
	}


@frappe.whitelist()
def analytics(name, period="1 hour"):
	interval, divisor, = {
		"1 hour": ("1 HOUR", 60),
		"6 hours": ("6 HOUR", 5 * 60),
		"24 hours": ("24 HOUR", 30 * 60),
		"7 days": ("7 DAY", 3 * 60 * 60),
		"30 days": ("30 DAY", 12 * 60 * 60),
	}[period]

	def get_data(doctype, fields):
		query = f"""
			SELECT
				{fields},
				FROM_UNIXTIME({divisor} * (UNIX_TIMESTAMP(timestamp) DIV {divisor})) as _timestamp
			FROM
				`tab{doctype}`
			WHERE
				site = %s AND timestamp >= UTC_TIMESTAMP() - INTERVAL {interval}
			GROUP BY
				_timestamp
		"""
		result = frappe.db.sql(query, name, as_dict=True, debug=False)
		for row in result:
			row["timestamp"] = row.pop("_timestamp")
		return result

	request_data = get_data(
		"Site Request Log", "COUNT(name) as request_count, SUM(duration) as request_duration"
	)
	job_data = get_data(
		"Site Job Log", "COUNT(name) as job_count, SUM(duration) as job_duration"
	)
	uptime_data = get_data(
		"Site Uptime Log",
		"AVG(web) AS web, AVG(scheduler) AS scheduler, AVG(socketio) AS socketio",
	)
	return {
		"request_count": [
			{"value": r.request_count, "timestamp": r.timestamp} for r in request_data
		],
		"request_cpu_time": [
			{"value": r.request_duration, "timestamp": r.timestamp} for r in request_data
		],
		"job_count": [{"value": r.job_count, "timestamp": r.timestamp} for r in job_data],
		"job_cpu_time": [
			{"value": r.job_duration, "timestamp": r.timestamp} for r in job_data
		],
		"uptime": uptime_data,
	}


@frappe.whitelist()
def login(name):
	return frappe.get_doc("Site", name).login()


@frappe.whitelist()
def schedule_backup(name):
	frappe.get_doc("Site", name).perform_backup()
