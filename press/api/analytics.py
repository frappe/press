# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
import requests
import json
import sqlparse
from press.api.site import protected
from press.press.doctype.plan.plan import get_plan_config
from frappe.utils import (
	convert_utc_to_timezone,
	get_datetime,
	get_datetime_str,
	get_system_timezone,
)
from frappe.utils.password import get_decrypted_password
from datetime import datetime
from press.agent import Agent
from press.press.report.binary_log_browser.binary_log_browser import (
	get_files_in_timespan,
	convert_user_timezone_to_utc,
)

try:
	from frappe.utils import convert_utc_to_user_timezone
except ImportError:
	from frappe.utils import convert_utc_to_system_timezone as convert_utc_to_user_timezone


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
	request_count_by_path_data = get_request_by_path(
		name, "count", timezone, timespan, timegrain
	)
	request_duration_by_path_data = get_request_by_path(
		name, "duration", timezone, timespan, timegrain
	)
	job_data = get_usage(name, "job", timezone, timespan, timegrain)

	uptime_data = get_uptime(name, timezone, timespan, timegrain)

	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan)["rate_limit"]["limit"]

	return {
		"usage_counter": [{"value": r.max, "date": r.date} for r in request_data],
		"request_count": [{"value": r.count, "date": r.date} for r in request_data],
		"request_cpu_time": [{"value": r.duration, "date": r.date} for r in request_data],
		"request_count_by_path": request_count_by_path_data,
		"request_duration_by_path": request_duration_by_path_data,
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
			f'sum(sum_over_time(probe_success{{job="site", instance="{site}"}}[{timegrain}s])) by (instance) / sum(count_over_time(probe_success{{job="site", instance="{site}"}}[{timegrain}s])) by (instance)'
		),
		"start": start.timestamp(),
		"end": end.timestamp(),
		"step": f"{timegrain}s",
	}

	response = requests.get(url, params=query, auth=("frappe", password)).json()

	buckets = []
	if not response["data"]["result"]:
		return []
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


def get_request_by_path(site, query_type, timezone, timespan, timegrain):
	MAX_NO_OF_PATHS = 10

	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return {"datasets": [], "labels": []}

	url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	count_query = {
		"aggs": {
			"method_path": {
				"terms": {
					"field": "json.request.path",
					"order": {"request_count": "desc"},
					"size": MAX_NO_OF_PATHS,
				},
				"aggs": {
					"request_count": {
						"filter": {
							"bool": {
								"filter": [
									{"match_phrase": {"json.site": site}},
									{"range": {"@timestamp": {"gte": f"now-{timespan}s", "lte": "now"}}},
								],
								"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
							}
						}
					},
					"histogram_of_method": {
						"date_histogram": {
							"field": "@timestamp",
							"fixed_interval": f"{timegrain}s",
							"time_zone": timezone,
						},
						"aggs": {
							"request_count": {
								"filter": {
									"bool": {
										"filter": [
											{"match_phrase": {"json.site": site}},
											{"range": {"@timestamp": {"gte": f"now-{timespan}s", "lte": "now"}}},
										],
										"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
									}
								}
							}
						},
					},
				},
			}
		},
		"size": 0,
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.site": site}},
					{"range": {"@timestamp": {"gte": f"now-{timespan}s", "lte": "now"}}},
				],
				"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
			}
		},
	}

	duration_query = {
		"aggs": {
			"method_path": {
				"terms": {
					"field": "json.request.path",
					"order": {"methods>sum": "desc"},
					"size": MAX_NO_OF_PATHS,
				},
				"aggs": {
					"methods": {
						"filter": {
							"bool": {
								"filter": [
									{"match_phrase": {"json.site": site}},
									{"range": {"@timestamp": {"gte": f"now-{timespan}s", "lte": "now"}}},
								],
								"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
							}
						},
						"aggs": {
							"sum": {
								"sum": {
									"field": "json.duration",
								}
							}
						},
					},
					"histogram_of_method": {
						"date_histogram": {
							"field": "@timestamp",
							"fixed_interval": f"{timegrain}s",
							"time_zone": timezone,
						},
						"aggs": {
							"methods": {
								"filter": {
									"bool": {
										"filter": [
											{"match_phrase": {"json.site": site}},
											{"range": {"@timestamp": {"gte": f"now-{timespan}s", "lte": "now"}}},
										],
										"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
									}
								},
								"aggs": {
									"sum": {
										"sum": {
											"field": "json.duration",
										}
									}
								},
							},
						},
					},
				},
			},
		},
		"size": 0,
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.site": site}},
					{"range": {"@timestamp": {"gte": f"now-{timespan}s", "lte": "now"}}},
				],
				"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
			}
		},
	}

	if query_type == "count":
		query = count_query
	else:
		query = duration_query

	response = requests.post(url, json=query, auth=("frappe", password)).json()

	if not response["aggregations"]["method_path"]["buckets"]:
		return {"datasets": [], "labels": []}

	buckets = []
	labels = [
		get_datetime(data["key_as_string"]).replace(tzinfo=None)
		for data in response["aggregations"]["method_path"]["buckets"][0][
			"histogram_of_method"
		]["buckets"]
	]
	for bucket in response["aggregations"]["method_path"]["buckets"]:
		buckets.append(
			frappe._dict(
				{
					"path": bucket["key"],
					"values": [
						data["request_count"]["doc_count"]
						if query_type == "count"
						else data["methods"]["sum"]["value"] / 1000000
						if query_type == "duration"
						else 0
						for data in bucket["histogram_of_method"]["buckets"]
					],
					"stack": "path",
				}
			)
		)

	return {"datasets": buckets, "labels": labels}


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


def multi_get_current_cpu_usage(sites):
	try:
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if not log_server:
			return [0] * len(sites)

		url = f"https://{log_server}/elasticsearch/filebeat-*/_msearch"
		password = get_decrypted_password("Log Server", log_server, "kibana_password")

		headers = ["{}"] * len(sites)
		bodies = [
			json.dumps(
				{
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
			)
			for site in sites
		]

		multi_query = [None] * 2 * len(sites)
		multi_query[::2] = headers
		multi_query[1::2] = bodies

		payload = "\n".join(multi_query) + "\n"

		response = requests.post(
			url,
			data=payload,
			auth=("frappe", password),
			headers={"Content-Type": "application/x-ndjson"},
		).json()

		result = []
		for response in response["responses"]:
			hits = response["hits"]["hits"]
			if hits:
				result.append(hits[0]["_source"]["json"]["request"].get("counter", 0))
			else:
				result.append(0)
		return result
	except Exception:
		return [0] * len(sites)


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


@frappe.whitelist()
@protected("Site")
def binary_logs(name, start_time, end_time, pattern=".*", max_lines=4000):
	site_doc = frappe.get_doc("Site", name)

	db_server = frappe.db.get_value("Server", site_doc.server, "database_server")
	agent = Agent(db_server, "Database Server")

	data = {
		"database": site_doc.database_name,
		"start_datetime": convert_user_timezone_to_utc(start_time),
		"stop_datetime": convert_user_timezone_to_utc(end_time),
		"search_pattern": pattern,
		"max_lines": max_lines,
	}

	files = agent.get("database/binary/logs")

	files_in_timespan = get_files_in_timespan(files, start_time, end_time)

	out = []
	for file in files_in_timespan:
		print(file)
		rows = agent.post(f"database/binary/logs/{file}", data=data)
		print(rows)
		for row in rows:
			row["query"] = sqlparse.format(
				row["query"].strip(), keyword_case="upper", reindent=True
			)
			row["timestamp"] = get_datetime_str(
				convert_utc_to_user_timezone(get_datetime(row["timestamp"]))
			)
			out.append(row)

			if len(out) >= max_lines:
				return out

	return out


@frappe.whitelist()
@protected("Site")
def mariadb_processlist(site):
	site = frappe.get_doc("Site", site)
	dbserver = frappe.db.get_value("Server", site.server, "database_server")
	db_doc = frappe.get_doc("Database Server", dbserver)
	agent = Agent(db_doc.name, "Database Server")

	data = {
		"private_ip": db_doc.private_ip,
		"mariadb_root_password": db_doc.get_password("mariadb_root_password"),
	}
	rows = agent.post("database/processes", data=data)

	out = []
	for row in rows:
		row["Info"] = sqlparse.format(
			(row["Info"] or "").strip(), keyword_case="upper", reindent=True
		)
		if row["db"] == site.database_name:
			out.append(row)

	return out


@frappe.whitelist()
@protected("Site")
def mariadb_slow_queries(site, start, end, pattern=".*", max_lines=100):
	from press.press.report.mariadb_slow_queries.mariadb_slow_queries import (
		get_slow_query_logs,
	)

	db_name = frappe.db.get_value("Site", site, "database_name")
	rows = get_slow_query_logs(
		db_name,
		convert_user_timezone_to_utc(start),
		convert_user_timezone_to_utc(end),
		pattern,
		max_lines,
	)

	for row in rows:
		row["query"] = sqlparse.format(
			row["query"].strip(), keyword_case="upper", reindent=True
		)
		row["timestamp"] = convert_utc_to_timezone(
			frappe.utils.get_datetime(row["timestamp"]).replace(tzinfo=None),
			get_system_timezone(),
		)
	return rows


@frappe.whitelist()
@protected("Site")
def deadlock_report(site, start, end, max_lines=20):
	from press.press.report.mariadb_deadlock_browser.mariadb_deadlock_browser import (
		post_process,
	)

	server = frappe.db.get_value("Site", site, "server")
	db_server_name = frappe.db.get_value("Server", server, "database_server")
	database_server = frappe.get_doc("Database Server", db_server_name)
	agent = Agent(database_server.name, "Database Server")

	data = {
		"private_ip": database_server.private_ip,
		"mariadb_root_password": database_server.get_password("mariadb_root_password"),
		"database": database_server.name,
		"start_datetime": convert_user_timezone_to_utc(start),
		"stop_datetime": convert_user_timezone_to_utc(end),
		"max_lines": max_lines,
	}

	results = agent.post("database/deadlocks", data=data)

	out = post_process(results)

	return out


# MARKETPLACE - Plausible
@frappe.whitelist(allow_guest=True)
@protected("Marketplace App")
def plausible_analytics(name):
	response = {}
	settings = frappe.get_single("Press Settings")
	api_endpoints = {
		"aggregate": "/api/v1/stats/aggregate",
		"timeseries": "/api/v1/stats/timeseries",
	}
	params = {
		"site_id": settings.plausible_site_id,
		"period": "30d",
		"metrics": "visitors,pageviews",
		"filters": f"visit:page==/marketplace/apps/{name}",
	}
	headers = {"Authorization": f'Bearer {settings.get_password("plausible_api_key")}'}

	for api_type, endpoint in api_endpoints.items():
		res = requests.get(settings.plausible_url + endpoint, params=params, headers=headers)
		if res.status_code == 200 and res.json().get("results"):
			res = res.json().get("results")
			if api_type == "aggregate":
				response.update(
					{"agg_pageviews": res["pageviews"], "agg_visitors": res["visitors"]}
				)
			elif api_type == "timeseries":
				pageviews = [{"value": d["pageviews"], "date": d["date"]} for d in res]
				unique_visitors = [{"value": d["visitors"], "date": d["date"]} for d in res]
				response.update({"pageviews": pageviews, "visitors": unique_visitors})

	return response
