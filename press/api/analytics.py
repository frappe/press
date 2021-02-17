# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from press.api.site import protected
from press.press.doctype.plan.plan import get_plan_config
import frappe


@frappe.whitelist()
@protected("Site")
def get(name, period="1 hour"):
	usage_data = get_data(name, "Site Request Log", "duration", period)
	request_data = get_data(
		name,
		"Site Request Log",
		"COUNT(name) as request_count, SUM(duration) as request_duration",
		period,
	)
	job_data = get_data(
		name,
		"Site Job Log",
		"COUNT(name) as job_count, SUM(duration) as job_duration",
		period,
	)
	uptime_data = get_data(
		name,
		"Site Uptime Log",
		"AVG(web) AS web, AVG(scheduler) AS scheduler, AVG(socketio) AS socketio",
		period,
	)
	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan)["rate_limit"]["limit"]
	return {
		"usage_counter": [
			{"value": r.duration, "timestamp": r.timestamp} for r in usage_data
		],
		"request_count": [
			{"value": r.request_count, "timestamp": r.timestamp} for r in request_data
		],
		"request_cpu_time": [
			{"value": r.request_duration, "timestamp": r.timestamp} for r in request_data
		],
		"job_count": [{"value": r.job_count, "timestamp": r.timestamp} for r in job_data],
		"job_cpu_time": [
			{"value": r.job_duration * 1000, "timestamp": r.timestamp} for r in job_data
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


def get_data(site, doctype, fields, period):
	interval, divisor, = {
		"1 hour": ("1 HOUR", 60),
		"6 hours": ("6 HOUR", 5 * 60),
		"24 hours": ("24 HOUR", 30 * 60),
		"7 days": ("7 DAY", 3 * 60 * 60),
		"30 days": ("30 DAY", 12 * 60 * 60),
	}[period]
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
	result = frappe.db.sql(query, site, as_dict=True, debug=False)
	for row in result:
		row["timestamp"] = row.pop("_timestamp")
	return result
