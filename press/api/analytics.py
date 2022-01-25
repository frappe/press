# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe
import requests

from press.api.site import protected
from press.press.doctype.plan.plan import get_plan_config
from frappe.utils import convert_utc_to_timezone, get_datetime
from frappe.utils.password import get_decrypted_password
from datetime import datetime


@frappe.whitelist()
@protected("Site")
def get(name, timezone, duration="7d"):

	timespan, timegrain = {
		"1h": (60 * 60, 60),
		"6h": (6 * 60 * 60, 5 * 60),
		"24h": (24 * 60 * 60, 30 * 60),
		"7d": (7 * 24 * 60 * 60, 3 * 60 * 60),
		"15d": (15 * 24 * 60 * 60, 6 * 60 * 60),
	}[duration]

	request_data = get_usage(name, "request", timezone, timespan, timegrain)
	job_data = get_usage(name, "job", timezone, timespan, timegrain)

	uptime_data = get_uptime(name, timezone, timespan, timegrain)

	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan)["rate_limit"]["limit"]

	return {
		"usage_counter": [{"value": r.max, "date": r.date} for r in request_data],
		"request_count": [{"value": r.count, "date": r.date} for r in request_data],
		"request_cpu_time": [{"value": r.duration, "date": r.date} for r in request_data],
		"job_count": [{"value": r.count, "date": r.date} for r in job_data],
		"job_cpu_time": [{"value": r.duration, "date": r.date} for r in job_data],
		"uptime": (uptime_data + [{}] * 60)[:60],
		"plan_limit": plan_limit,
	}


@frappe.whitelist()
@protected("Site")
def daily_usage(name, timezone):
	timespan = 7 * 24 * 60 * 60
	timegrain = 24 * 60 * 60
	request_data = get_usage(name, "request", timezone, timespan, timegrain)

	plan = frappe.get_cached_doc("Site", name).plan

	return {
		"data": [{"value": r.max, "date": r.date} for r in request_data],
		"plan_limit": get_plan_config(plan)["rate_limit"]["limit"] if plan else 0,
	}


def get_uptime(site, timezone, timespan, timegrain):
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		return []

	url = f"https://{monitor_server}/prometheus/api/v1/query_range"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")

	end = frappe.utils.now_datetime()
	start = frappe.utils.add_to_date(end, seconds=-timespan)
	query = {
		"query": (
			f'avg_over_time(probe_success{{job="site", instance="{site}"}}[{timegrain}s])'
		),
		"start": start.timestamp(),
		"end": end.timestamp(),
		"step": f"{timegrain}s",
	}

	response = requests.get(url, params=query, auth=("frappe", password)).json()

	buckets = []
	for timestamp, value in response["data"]["result"][0]["values"]:
		buckets.append(
			frappe._dict(
				{
					"date": convert_utc_to_timezone(
						datetime.fromtimestamp(timestamp).replace(tzinfo=None), timezone
					),
					"value": float(value),
				}
			)
		)
	return buckets


def get_usage(site, type, timezone, timespan, timegrain):
	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return []

	url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	query = {
		"aggs": {
			"date_histogram": {
				"date_histogram": {"field": "@timestamp", "fixed_interval": f"{timegrain}s"},
				"aggs": {
					"duration": {"sum": {"field": "json.duration"}},
					"count": {"value_count": {"field": "json.duration"}},
					"max": {"max": {"field": "json.request.counter"}},
				},
			}
		},
		"size": 0,
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.transaction_type": type}},
					{"match_phrase": {"json.site": site}},
					{"range": {"@timestamp": {"gte": f"now-{timespan}s", "lte": "now"}}},
				]
			}
		},
	}

	response = requests.post(url, json=query, auth=("frappe", password)).json()

	buckets = []
	for bucket in response["aggregations"]["date_histogram"]["buckets"]:
		buckets.append(
			frappe._dict(
				{
					"date": convert_utc_to_timezone(
						get_datetime(bucket["key_as_string"]).replace(tzinfo=None), timezone
					),
					"count": bucket["count"]["value"],
					"duration": bucket["duration"]["value"],
					"max": bucket["max"]["value"],
				}
			)
		)
	return buckets


def get_current_cpu_usage(site):
	try:
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if not log_server:
			return 0

		url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
		password = get_decrypted_password("Log Server", log_server, "kibana_password")

		query = {
			"query": {
				"bool": {
					"filter": [
						{"match_phrase": {"json.transaction_type": "request"}},
						{"match_phrase": {"json.site": site}},
					]
				}
			},
			"sort": {"@timestamp": "desc"},
			"size": 1,
		}

		response = requests.post(url, json=query, auth=("frappe", password)).json()
		hits = response["hits"]["hits"]
		if hits:
			return hits[0]["_source"]["json"]["request"].get("counter", 0)
		return 0
	except Exception:
		return 0


@frappe.whitelist()
@protected("Site")
def request_logs(name, timezone, date, sort=None, start=0):
	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return []

	url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	sort_value = {
		"Time (Ascending)": {"@timestamp": "asc"},
		"Time (Descending)": {"@timestamp": "desc"},
		"CPU Time (Descending)": {"json.duration": "desc"},
	}[sort or "CPU Time (Descending)"]

	query = {
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.transaction_type": "request"}},
					{"match_phrase": {"json.site": name}},
					{"range": {"@timestamp": {"gt": f"{date}||-1d/d", "lte": f"{date}||/d"}}},
				],
				"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
			}
		},
		"sort": sort_value,
		"from": start,
		"size": 10,
	}

	response = requests.post(url, json=query, auth=("frappe", password)).json()
	out = []
	for d in response["hits"]["hits"]:
		data = d["_source"]["json"]
		data["timestamp"] = convert_utc_to_timezone(
			frappe.utils.get_datetime(data["timestamp"]).replace(tzinfo=None), timezone
		)
		out.append(data)
	return out
