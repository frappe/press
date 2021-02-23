# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from press.api.site import protected
from press.press.doctype.plan.plan import get_plan_config
import frappe


@frappe.whitelist()
@protected("Site")
def get(name, timezone):
	usage_data = get_data(name, "Site Request Log", "SUM(duration) as value", timezone)
	request_data = get_data(
		name,
		"Site Request Log",
		"COUNT(name) as request_count, SUM(duration) as request_duration",
		timezone,
	)
	job_data = get_data(
		name,
		"Site Job Log",
		"COUNT(name) as job_count, SUM(duration) as job_duration",
		timezone,
	)
	uptime_data = get_data(
		name,
		"Site Uptime Log",
		"AVG(web) AS web, AVG(scheduler) AS scheduler, AVG(socketio) AS socketio",
		timezone,
	)
	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan)["rate_limit"]["limit"]
	return {
		"usage_counter": usage_data,
		"request_count": [
			{"value": r.request_count, "date": r.date} for r in request_data
		],
		"request_cpu_time": [
			{"value": r.request_duration, "date": r.date} for r in request_data
		],
		"job_count": [{"value": r.job_count, "date": r.date} for r in job_data],
		"job_cpu_time": [
			{"value": r.job_duration * 1000, "date": r.date} for r in job_data
		],
		"uptime": (uptime_data + [{}] * 60)[:60],
		"plan_limit": plan_limit,
	}


@frappe.whitelist()
@protected("Site")
def request_counter(name, period="1 hour"):
	usage_data = get_data(name, "Site Request Log", "duration as value", period)
	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan)["rate_limit"]["limit"]
	return {
		"data": usage_data,
		"plan_limit": plan_limit,
	}


@frappe.whitelist()
@protected("Site")
def daily_usage(name):
	data = frappe.db.get_all(
		"Site Request Log",
		fields=["SUM(duration) as value", "DATE(timestamp) as date"],
		filters={"site": name, "timestamp": (">=", frappe.utils.add_days(None, -7))},
		group_by="date",
		order_by="date asc",
	)
	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan)["rate_limit"]["limit"]
	return dict(data=data, plan_limit=plan_limit)


def get_data(site, doctype, fields, timezone):
	return frappe.db.get_all(
		doctype,
		# CONVERT_TZ requires timezone data to be loaded first: https://stackoverflow.com/a/28015283
		fields=[f"DATE(CONVERT_TZ(timestamp, 'UTC', '{timezone}')) as date", fields],
		filters={
			"site": site,
			"timestamp": (">=", frappe.utils.add_days(frappe.utils.today(), -7)),
		},
		group_by="date",
		order_by="date asc",
	)
