# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Final, TypedDict

import frappe
import requests
import sqlparse
from elasticsearch import Elasticsearch
from elasticsearch_dsl import A, Search
from frappe.utils import (
	convert_utc_to_timezone,
	flt,
	get_datetime,
)
from frappe.utils.password import get_decrypted_password
from pytz import timezone as pytz_timezone

from press.agent import Agent
from press.api.site import protected
from press.press.doctype.site_plan.site_plan import get_plan_config
from press.press.report.binary_log_browser.binary_log_browser import (
	convert_user_timezone_to_utc,
)
from press.press.report.binary_log_browser.binary_log_browser import (
	get_data as get_binary_log_data,
)
from press.press.report.mariadb_slow_queries.mariadb_slow_queries import execute, normalize_query

if TYPE_CHECKING:
	from elasticsearch_dsl.response import AggResponse
	from elasticsearch_dsl.response.aggs import FieldBucket, FieldBucketData

	class Dataset(TypedDict):
		"""Single element of list of Datasets returned for stacked histogram chart"""

		path: str
		values: list[float, int]  # List of values for each timestamp [43.0, 0, 0...]
		stack: Final[str]

	class HistBucket(FieldBucket):
		key_as_string: str
		avg_of_duration: AggResponse
		sum_of_duration: AggResponse
		doc_count: int
		key: int

	class HistogramOfMethod(FieldBucketData):
		buckets: list[HistBucket]

	class PathBucket(FieldBucket):
		key: str
		histogram_of_method: HistogramOfMethod


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
	uptime_data = get_uptime(name, timezone, timespan, timegrain)

	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan).get("rate_limit", {}).get("limit") if plan else 0

	return {
		"usage_counter": [{"value": r.max, "date": r.date} for r in request_data],
		"request_count": [{"value": r.count, "date": r.date} for r in request_data],
		"request_cpu_time": [{"value": r.duration, "date": r.date} for r in request_data],
		"uptime": (uptime_data + [{}] * 60)[:60],
		"plan_limit": plan_limit,
	}


@frappe.whitelist()
def get_advanced_analytics(name, timezone, duration="7d"):
	timespan, timegrain = {
		"1h": (60 * 60, 60),
		"6h": (6 * 60 * 60, 5 * 60),
		"24h": (24 * 60 * 60, 30 * 60),
		"7d": (7 * 24 * 60 * 60, 3 * 60 * 60),
		"15d": (15 * 24 * 60 * 60, 6 * 60 * 60),
	}[duration]

	request_count_by_path_data = get_request_by_path(name, "count", timezone, timespan, timegrain)
	request_duration_by_path_data = get_request_by_path(name, "duration", timezone, timespan, timegrain)
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

	return {
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


def get_rounded_boundaries(timespan: int, timegrain: int, timezone: str = "UTC"):
	"""
	Round the start and end time to the nearest interval, because Elasticsearch does this
	"""
	end = datetime.now(pytz_timezone(timezone))
	start = frappe.utils.add_to_date(end, seconds=-timespan)

	return rounded_time(start, timegrain), rounded_time(end, timegrain)


def get_uptime(site, timezone, timespan, timegrain):
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		return []

	url = f"https://{monitor_server}/prometheus/api/v1/query_range"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")

	end = datetime.now(pytz_timezone(timezone))
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
					"date": convert_utc_to_timezone(datetime.fromtimestamp(timestamp), timezone),
					"value": float(value),
				}
			)
		)
	return buckets


def normalize_datasets(datasets: list[Dataset]) -> list[Dataset]:
	"""Merge similar queries and sum their durations/counts"""
	n_datasets = {}
	for data_dict in datasets:
		n_query = normalize_query(data_dict["path"])
		if n_datasets.get(n_query):
			n_datasets[n_query]["values"] = [
				x + y for x, y in zip(n_datasets[n_query]["values"], data_dict["values"])
			]
		else:
			data_dict["path"] = n_query
			n_datasets[n_query] = data_dict
	return list(n_datasets.values())


def get_stacked_histogram_chart_result(
	search: Search,
	query_type: str,
	start: datetime,
	end: datetime,
	timegrain: int,
	to_s_divisor: int = 1e6,
	normalize_slow_logs: bool = False,
) -> dict[list[Dataset], list[datetime]]:
	aggs: AggResponse = search.execute().aggregations

	timegrain = timedelta(seconds=timegrain)
	labels = [start + i * timegrain for i in range((end - start) // timegrain + 1)]
	# method_path has buckets of timestamps with method(eg: avg) of that duration
	datasets = []

	path_bucket: PathBucket
	for path_bucket in aggs.method_path.buckets:
		path_data = frappe._dict(
			{
				"path": path_bucket.key,
				"values": [0] * len(labels),
				"stack": "path",
			}
		)
		hist_bucket: HistBucket
		for hist_bucket in path_bucket.histogram_of_method.buckets:
			label = get_datetime(hist_bucket.key_as_string)
			if label not in labels:
				continue
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

	if normalize_slow_logs:
		datasets = normalize_datasets(datasets)

	labels = [label.replace(tzinfo=None) for label in labels]
	return {"datasets": datasets, "labels": labels}


def get_request_by_path(site, query_type, timezone, timespan, timegrain):
	MAX_NO_OF_PATHS = 10

	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return {"datasets": [], "labels": []}

	url = f"https://{log_server}/elasticsearch"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	start, end = get_rounded_boundaries(timespan, timegrain, timezone)

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

		search.aggs["method_path"].bucket("path_count", "value_count", field="json.request.path")

	elif query_type == "duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.request.path",
			size=MAX_NO_OF_PATHS,
			order={"outside_sum": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket("sum_of_duration", sum_of_duration)
		search.aggs["method_path"].bucket("outside_sum", sum_of_duration)  # for sorting

	elif query_type == "average_duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.request.path",
			size=MAX_NO_OF_PATHS,
			order={"outside_avg": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket("avg_of_duration", avg_of_duration)

		search.aggs["method_path"].bucket("outside_avg", avg_of_duration)  # for sorting

	return get_stacked_histogram_chart_result(search, query_type, start, end, timegrain)


def get_background_job_by_method(site, query_type, timezone, timespan, timegrain):
	MAX_NO_OF_PATHS = 10

	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		return {"datasets": [], "labels": []}

	url = f"https://{log_server}/elasticsearch"
	password = get_decrypted_password("Log Server", log_server, "kibana_password")

	start, end = get_rounded_boundaries(timespan, timegrain, timezone)

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

		search.aggs["method_path"].bucket("method_count", "value_count", field="json.job.method")

	elif query_type == "duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.job.method",
			size=MAX_NO_OF_PATHS,
			order={"outside_sum": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket("sum_of_duration", sum_of_duration)
		search.aggs["method_path"].bucket("outside_sum", sum_of_duration)  # for sorting

	elif query_type == "average_duration":
		search.aggs.bucket(
			"method_path",
			"terms",
			field="json.job.method",
			size=MAX_NO_OF_PATHS,
			order={"outside_avg": "desc"},
		).bucket("histogram_of_method", histogram_of_method).bucket("avg_of_duration", avg_of_duration)

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

	start, end = get_rounded_boundaries(timespan, timegrain, timezone)

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
			"wildcard",
			mysql__slowlog__query="SELECT /\*!40001 SQL_NO_CACHE \*/*",  # noqa
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
		).bucket("histogram_of_method", histogram_of_method).bucket("sum_of_duration", sum_of_duration)
		search.aggs["method_path"].bucket("outside_sum", sum_of_duration)

	return get_stacked_histogram_chart_result(
		search, query_type, start, end, timegrain, to_s_divisor=1e9, normalize_slow_logs=True
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


def get_current_cpu_usage_for_sites_on_server(server):
	result = {}
	with suppress(Exception):
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if not log_server:
			return result

		url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
		password = get_decrypted_password("Log Server", log_server, "kibana_password")

		query = {
			"aggs": {
				"0": {
					"terms": {"field": "json.site", "size": 1000},
					"aggs": {
						"usage": {
							"filter": {"exists": {"field": "json.request.counter"}},
							"aggs": {
								"counter": {
									"top_metrics": {
										"metrics": {"field": "json.request.counter"},
										"size": 1,
										"sort": {"@timestamp": "desc"},
									}
								}
							},
						}
					},
				}
			},
			"size": 0,
			"query": {
				"bool": {
					"filter": [
						{
							"bool": {
								"filter": [
									{
										"bool": {
											"should": [
												{"term": {"json.transaction_type": {"value": "request"}}}
											],
											"minimum_should_match": 1,
										}
									},
									{
										"bool": {
											"should": [{"term": {"agent.name": {"value": server}}}],
											"minimum_should_match": 1,
										}
									},
								]
							}
						},
						{"range": {"@timestamp": {"gte": "now-1d"}}},
					]
				}
			},
		}

		response = requests.post(url, json=query, auth=("frappe", password)).json()
		for row in response["aggregations"]["0"]["buckets"]:
			site = row["key"]
			metric = row["usage"]["counter"]["top"]
			if metric:
				result[site] = metric[0]["metrics"]["json.request.counter"]
		return result


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
def binary_logs(name, start_time, end_time, pattern: str = ".*", max_lines: int = 4000):
	filters = frappe._dict(
		site=name,
		database=frappe.db.get_value("Site", name, "database_name"),
		start_datetime=start_time,
		stop_datetime=end_time,
		pattern=pattern,
		max_lines=max_lines,
	)

	return get_binary_log_data(filters)


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
		row["Info"] = sqlparse.format((row["Info"] or "").strip(), keyword_case="upper", reindent=True)
		if row["db"] == site.database_name:
			out.append(row)

	return out


@frappe.whitelist()
@protected("Site")
def mariadb_slow_queries(
	name,
	start_datetime,
	stop_datetime,
	max_lines=1000,
	search_pattern=".*",
	normalize_queries=True,
	analyze=False,
):
	meta = frappe._dict(
		{
			"site": name,
			"start_datetime": start_datetime,
			"stop_datetime": stop_datetime,
			"max_lines": max_lines,
			"search_pattern": search_pattern,
			"normalize_queries": normalize_queries,
			"analyze": analyze,
		}
	)
	columns, data = execute(filters=meta)
	return {"columns": columns, "data": data}


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

	return post_process(results)


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
				response.update({"agg_pageviews": res["pageviews"], "agg_visitors": res["visitors"]})
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


def get_doctype_name(table_name: str) -> str:
	return table_name.removeprefix("tab")


@frappe.whitelist()
@protected("Site")
def mariadb_add_suggested_index(name, table, column):
	record_exists = frappe.db.exists(
		"Agent Job",
		{
			"site": name,
			"status": ["in", ["Undelivered", "Running", "Pending"]],
			"job_type": "Add Database Index",
		},
	)
	if record_exists:
		frappe.throw("There is already a pending job for Add Database Index. Please wait until finished.")
	doctype = get_doctype_name(table)
	site = frappe.get_cached_doc("Site", name)
	agent = Agent(site.server)
	agent.add_database_index(site, doctype=doctype, columns=[column])
