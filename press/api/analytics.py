# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, A
import frappe
import requests
import json
import sqlparse
from frappe.utils import flt
from press.api.site import protected
from press.press.doctype.site_plan.site_plan import get_plan_config
from frappe.utils import (
	convert_utc_to_timezone,
	get_datetime,
	get_datetime_str,
	get_system_timezone,
)
from frappe.utils.password import get_decrypted_password
from datetime import datetime, timedelta
from press.agent import Agent
from press.press.report.binary_log_browser.binary_log_browser import (
	get_files_in_timespan,
	convert_user_timezone_to_utc,
)


try:
	from frappe.utils import convert_utc_to_user_timezone
except ImportError:
	from frappe.utils import (
		convert_utc_to_system_timezone as convert_utc_to_user_timezone,
	)


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
	average_request_duration_by_path_data = get_request_by_path(
		name, "average_duration", timezone, timespan, timegrain
	)
	background_job_count_by_method_data = get_background_job_by_method(
		name, "count", timezone, timespan, timegrain
	)
	background_job_duration_by_method_data = get_background_job_by_method(
		name, "duration", timezone, timespan, timegrain
	)
	average_background_job_duration_by_method_data = get_background_job_by_method(
		name, "average_duration", timezone, timespan, timegrain
	)
	slow_logs_by_count = get_slow_logs(name, "count", timezone, timespan, timegrain)
	slow_logs_by_duration = get_slow_logs(name, "duration", timezone, timespan, timegrain)
	job_data = get_usage(name, "job", timezone, timespan, timegrain)

	uptime_data = get_uptime(name, timezone, timespan, timegrain)

	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan).get("rate_limit", {}).get("limit") if plan else 0

	return {
		"usage_counter": [{"value": r.max, "date": r.date} for r in request_data],
		"request_count": [{"value": r.count, "date": r.date} for r in request_data],
		"request_cpu_time": [{"value": r.duration, "date": r.date} for r in request_data],
		"request_count_by_path": request_count_by_path_data,
		"request_duration_by_path": request_duration_by_path_data,
		"average_request_duration_by_path": average_request_duration_by_path_data,
		"background_job_count_by_method": background_job_count_by_method_data,
		"background_job_duration_by_method": background_job_duration_by_method_data,
		"average_background_job_duration_by_method": average_background_job_duration_by_method_data,
		"slow_logs_by_count": slow_logs_by_count,
		"slow_logs_by_duration": slow_logs_by_duration,
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


def rounded_time(dt=None, round_to=60):
	"""Round a datetime object to any time lapse in seconds
	dt : datetime.datetime object, default now.
	round_to : Closest number of seconds to round to, default 1 minute.
	ref: https://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object/10854034#10854034
	"""
	if dt is None:
		dt = datetime.datetime.now()
	seconds = (dt.replace(tzinfo=None) - dt.min).seconds
	rounding = (seconds + round_to / 2) // round_to * round_to
	return dt + timedelta(0, rounding - seconds, -dt.microsecond)


def get_rounded_boundaries(timespan: int, timegrain: int):
	"""
	Round the start and end time to the nearest interval, because Elasticsearch does this
	"""
	end = frappe.utils.now_datetime()
	start = frappe.utils.add_to_date(end, seconds=-timespan)

	return rounded_time(start, timegrain), rounded_time(end, timegrain)


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


def get_stacked_histogram_chart_result(
	search: Search,
	query_type: str,
	start: datetime,
	end: datetime,
	timegrain: int,
	to_s_divisor: int = 1e6,
):
	aggs = search.execute().aggregations

	timegrain = timedelta(seconds=timegrain)
	labels = [start + i * timegrain for i in range((end - start) // timegrain + 1)]
	# method_path has buckets of timestamps with method(eg: avg) of that duration
	datasets = []

	for path_bucket in aggs.method_path.buckets:
		path_data = frappe._dict(
			{
				"path": path_bucket.key,
				"values": [0] * len(labels),
				"stack": "path",
			}
		)
		for hist_bucket in path_bucket.histogram_of_method.buckets:
			label = get_datetime(hist_bucket.key_as_string).replace(tzinfo=None)
			if label in labels:
				path_data["values"][labels.index(label)] = (
					(flt(hist_bucket.avg_of_duration.value) / to_s_divisor)
					if query_type == "average_duration"
					else (
						flt(hist_bucket.sum_of_duration.value) / to_s_divisor
						if query_type == "duration"
						else hist_bucket.doc_count
						if query_type == "count"
						else 0
					)
				)
		datasets.append(path_data)

	return {"datasets": datasets, "labels": labels}


def get_request_by_path(site, query_type, timezone, timespan, timegrain):
	MAX_NO_OF_PATHS = 10

	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return {"datasets": [], "labels": []}

	url = f"https://{log_server}/elasticsearch"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	start, end = get_rounded_boundaries(timespan, timegrain)

	es = Elasticsearch(url, basic_auth=("frappe", password))
	search = (
		Search(using=es, index="filebeat-*")
		.filter("match_phrase", json__site=site)
		.filter("match_phrase", json__transaction_type="request")
		.filter(
			"range",
			**{
				"@timestamp": {
					"gte": int(start.timestamp() * 1000),
					"lte": int(end.timestamp() * 1000),
				}
			},
		)
		.exclude("match_phrase", json__request__path="/api/method/ping")
		.extra(size=0)
	)

	histogram_of_method = A(
		"date_histogram",
		field="@timestamp",
		fixed_interval=f"{timegrain}s",
		time_zone=timezone,
		min_doc_count=0,
	)
	avg_of_duration = A("avg", field="json.duration")
	sum_of_duration = A("sum", field="json.duration")

	if query_type == "count":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.request.path",
			size=MAX_NO_OF_PATHS,
			order={"path_count": "desc"},
		).bucket("histogram_of_method", histogram_of_method)

		search.aggs["method_path"].bucket(
			"path_count", "value_count", field="json.request.path"
		)

	elif query_type == "duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.request.path",
			size=MAX_NO_OF_PATHS,
			order={"outside_sum": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket(
			"sum_of_duration", sum_of_duration
		)
		search.aggs["method_path"].bucket("outside_sum", sum_of_duration)  # for sorting

	elif query_type == "average_duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.request.path",
			size=MAX_NO_OF_PATHS,
			order={"outside_avg": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket(
			"avg_of_duration", avg_of_duration
		)

		search.aggs["method_path"].bucket("outside_avg", avg_of_duration)  # for sorting

	return get_stacked_histogram_chart_result(search, query_type, start, end, timegrain)


def get_background_job_by_method(site, query_type, timezone, timespan, timegrain):
	MAX_NO_OF_PATHS = 10

	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return {"datasets": [], "labels": []}

	url = f"https://{log_server}/elasticsearch"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	start, end = get_rounded_boundaries(timespan, timegrain)

	es = Elasticsearch(url, basic_auth=("frappe", password))
	search = (
		Search(using=es, index="filebeat-*")
		.filter("match_phrase", json__site=site)
		.filter("match_phrase", json__transaction_type="job")
		.filter(
			"range",
			**{
				"@timestamp": {
					"gte": int(start.timestamp() * 1000),
					"lte": int(end.timestamp() * 1000),
				}
			},
		)
		.extra(size=0)
	)

	histogram_of_method = A(
		"date_histogram",
		field="@timestamp",
		fixed_interval=f"{timegrain}s",
		time_zone=timezone,
		min_doc_count=0,
	)
	avg_of_duration = A("avg", field="json.duration")
	sum_of_duration = A("sum", field="json.duration")

	if query_type == "count":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.job.method",
			size=MAX_NO_OF_PATHS,
			order={"method_count": "desc"},
		).bucket("histogram_of_method", histogram_of_method)

		search.aggs["method_path"].bucket(
			"method_count", "value_count", field="json.job.method"
		)

	elif query_type == "duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.job.method",
			size=MAX_NO_OF_PATHS,
			order={"outside_sum": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket(
			"sum_of_duration", sum_of_duration
		)
		search.aggs["method_path"].bucket("outside_sum", sum_of_duration)  # for sorting

	elif query_type == "average_duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.job.method",
			size=MAX_NO_OF_PATHS,
			order={"outside_avg": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket(
			"avg_of_duration", avg_of_duration
		)

		search.aggs["method_path"].bucket("outside_avg", avg_of_duration)  # for sorting

	return get_stacked_histogram_chart_result(search, query_type, start, end, timegrain)


def get_slow_logs(site, query_type, timezone, timespan, timegrain):
	database_name = frappe.db.get_value("Site", site, "database_name")
	MAX_NO_OF_PATHS = 10

	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server or not database_name:
		return {"datasets": [], "labels": []}

	url = f"https://{log_server}/elasticsearch/"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	start, end = get_rounded_boundaries(timespan, timegrain)

	es = Elasticsearch(url, basic_auth=("frappe", password))
	search = (
		Search(using=es, index="filebeat-*")
		.filter("match", mysql__slowlog__current_user=database_name)
		.filter(
			"range",
			**{
				"@timestamp": {
					"gte": int(start.timestamp() * 1000),
					"lte": int(end.timestamp() * 1000),
				}
			},
		)
		.exclude(
			"wildcard", mysql__slowlog__query="SELECT /\*!40001 SQL_NO_CACHE \*/*"  # noqa
		)
		.extra(size=0)
	)

	histogram_of_method = A(
		"date_histogram",
		field="@timestamp",
		fixed_interval=f"{timegrain}s",
		time_zone=timezone,
		min_doc_count=0,
	)
	sum_of_duration = A("sum", field="event.duration")

	if query_type == "count":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="mysql.slowlog.query",
			size=MAX_NO_OF_PATHS,
			order={"slowlog_count": "desc"},
		).bucket("histogram_of_method", histogram_of_method)

		search.aggs["method_path"].bucket(
			"slowlog_count",
			"value_count",
			field="mysql.slowlog.query",
		)
	elif query_type == "duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="mysql.slowlog.query",
			size=MAX_NO_OF_PATHS,
			order={"outside_sum": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket(
			"sum_of_duration", sum_of_duration
		)
		search.aggs["method_path"].bucket("outside_sum", sum_of_duration)

	return get_stacked_histogram_chart_result(
		search, query_type, start, end, timegrain, to_s_divisor=1e9
	)


def get_usage(site, type, timezone, timespan, timegrain):
	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return {"datasets": [], "labels": []}

	url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	query = {
		"aggs": {
			"date_histogram": {
				"date_histogram": {
					"field": "@timestamp",
					"fixed_interval": f"{timegrain}s",
				},
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
						get_datetime(bucket["key_as_string"]).replace(tzinfo=None),
						timezone,
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
	from press.utils import convert_user_timezone_to_utc

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

	response.update(
		{
			"weekly_installs": frappe.db.sql(
				f"""
		SELECT DATE_FORMAT(sa.creation, '%Y-%m-%d') AS date, COUNT(*) AS value
		FROM `tabSite Activity` as sa
		WHERE sa.action = 'Install App'
		AND sa.creation >= DATE_SUB(CURDATE(), INTERVAL 8 WEEK)
		AND sa.reason = '{name}'
		GROUP BY WEEK(sa.creation)
		ORDER BY date
		""",
				as_dict=True,
			),
		}
	)

	return response
