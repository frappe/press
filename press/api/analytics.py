# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta
from enum import Enum
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
from frappe.utils.caching import redis_cache
from frappe.utils.password import get_decrypted_password
from pytz import timezone as pytz_timezone

from press.agent import Agent
from press.api.site import protected
from press.press.doctype.site_plan.site_plan import get_plan_config
from press.press.report.binary_log_browser.binary_log_browser import (
	get_data as get_binary_log_data,
)
from press.press.report.mariadb_slow_queries.mariadb_slow_queries import execute, normalize_query

if TYPE_CHECKING:
	from elasticsearch_dsl.response import AggResponse
	from elasticsearch_dsl.response.aggs import FieldBucket, FieldBucketData

	from press.press.doctype.press_settings.press_settings import PressSettings

	class Dataset(TypedDict):
		"""Single element of list of Datasets returned for stacked histogram chart"""

		path: str
		values: list[float | int]  # List of values for each timestamp [43.0, 0, 0...]
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


class ResourceType(Enum):
	SITE = "site"
	SERVER = "server"


class AggType(Enum):
	COUNT = "count"
	DURATION = "duration"
	AVERAGE_DURATION = "average_duration"


TIMESPAN_TIMEGRAIN_MAP: Final[dict[str, tuple[int, int]]] = {
	"1h": (60 * 60, 60),
	"6h": (6 * 60 * 60, 5 * 60),
	"24h": (24 * 60 * 60, 30 * 60),
	"7d": (7 * 24 * 60 * 60, 3 * 60 * 60),
	"15d": (15 * 24 * 60 * 60, 6 * 60 * 60),
}


class StackedGroupByChart:
	search: Search
	to_s_divisor: float = 1e6
	normalize_slow_logs: bool = False
	group_by_field: str
	MAX_NO_OF_PATHS: int = 10

	def __init__(
		self,
		name: str,
		agg_type: AggType,
		resource_type: ResourceType,
		timezone: str,
		timespan: int,
		timegrain: int,
	):
		self.log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if not self.log_server:
			return

		self.url = f"https://{self.log_server}/elasticsearch"
		self.password = str(get_decrypted_password("Log Server", self.log_server, "kibana_password"))

		self.name = name
		self.agg_type = agg_type
		self.resource_type = resource_type
		self.timezone = timezone
		self.timespan = timespan
		self.timegrain = timegrain

		self.setup_search_filters()
		self.setup_search_aggs()

	def setup_search_filters(self):
		es = Elasticsearch(self.url, basic_auth=("frappe", self.password))
		self.start, self.end = get_rounded_boundaries(self.timespan, self.timegrain, self.timezone)
		self.search = (
			Search(using=es, index="filebeat-*")
			.filter(
				"range",
				**{
					"@timestamp": {
						"gte": int(self.start.timestamp() * 1000),
						"lte": int(self.end.timestamp() * 1000),
					}
				},
			)
			.extra(size=0)
		)

	def setup_search_aggs(self):
		if not self.group_by_field:
			frappe.throw("Group by field not set")
		if AggType(self.agg_type) is AggType.COUNT:
			self.search.aggs.bucket(
				"method_path",
				"terms",
				field=self.group_by_field,
				size=self.MAX_NO_OF_PATHS,
				order={"path_count": "desc"},
			).bucket("histogram_of_method", self.histogram_of_method())
			self.search.aggs["method_path"].bucket("path_count", self.count_of_values())

		elif AggType(self.agg_type) is AggType.DURATION:
			self.search.aggs.bucket(
				"method_path",
				"terms",
				field=self.group_by_field,
				size=self.MAX_NO_OF_PATHS,
				order={"outside_sum": "desc"},
			).bucket("histogram_of_method", self.histogram_of_method()).bucket(
				"sum_of_duration", self.sum_of_duration()
			)
			self.search.aggs["method_path"].bucket("outside_sum", self.sum_of_duration())  # for sorting

		elif AggType(self.agg_type) is AggType.AVERAGE_DURATION:
			self.search.aggs.bucket(
				"method_path",
				"terms",
				field=self.group_by_field,
				size=self.MAX_NO_OF_PATHS,
				order={"outside_avg": "desc"},
			).bucket("histogram_of_method", self.histogram_of_method()).bucket(
				"avg_of_duration", self.avg_of_duration()
			)
			self.search.aggs["method_path"].bucket("outside_avg", self.avg_of_duration())

	def histogram_of_method(self):
		return A(
			"date_histogram",
			field="@timestamp",
			fixed_interval=f"{self.timegrain}s",
			time_zone=self.timezone,
			min_doc_count=0,
		)

	def count_of_values(self):
		return A("value_count", field=self.group_by_field)

	def sum_of_duration(self):
		raise NotImplementedError

	def avg_of_duration(self):
		raise NotImplementedError

	def exclude_top_k_data(self, datasets: list[Dataset]):
		raise NotImplementedError

	def get_other_bucket(self, datasets: list[Dataset], labels):
		# filters present in search already, clear out aggs and response
		self.search.aggs._params = {}
		del self.search._response

		self.exclude_top_k_data(datasets)
		self.search.aggs.bucket("histogram_of_method", self.histogram_of_method())

		if AggType(self.agg_type) is AggType.COUNT:
			self.search.aggs["histogram_of_method"].bucket("path_count", self.count_of_values())
		elif AggType(self.agg_type) is AggType.DURATION:
			self.search.aggs["histogram_of_method"].bucket("sum_of_duration", self.sum_of_duration())
		elif AggType(self.agg_type) is AggType.AVERAGE_DURATION:
			self.search.aggs["histogram_of_method"].bucket("avg_of_duration", self.avg_of_duration())

		aggs = self.search.execute().aggregations

		aggs.key = "Other"  # Set custom key Other bucket
		return self.get_histogram_chart(aggs, labels)

	def get_histogram_chart(
		self,
		path_bucket: PathBucket,
		labels: list[datetime],
	):
		path_data = {
			"path": path_bucket.key,
			"values": [0] * len(labels),
			"stack": "path",
		}
		hist_bucket: HistBucket
		for hist_bucket in path_bucket.histogram_of_method.buckets:
			label = get_datetime(hist_bucket.key_as_string)
			if label not in labels:
				continue
			path_data["values"][labels.index(label)] = (
				(flt(hist_bucket.avg_of_duration.value) / self.to_s_divisor)
				if AggType(self.agg_type) is AggType.AVERAGE_DURATION
				else (
					flt(hist_bucket.sum_of_duration.value) / self.to_s_divisor
					if AggType(self.agg_type) is AggType.DURATION
					else hist_bucket.doc_count
					if AggType(self.agg_type) is AggType.COUNT
					else 0
				)
			)
		return path_data

	def get_stacked_histogram_chart(self):
		aggs: AggResponse = self.search.execute().aggregations

		timegrain_delta = timedelta(seconds=self.timegrain)
		labels = [
			self.start + i * timegrain_delta for i in range((self.end - self.start) // timegrain_delta + 1)
		]
		# method_path has buckets of timestamps with method(eg: avg) of that duration
		datasets = []

		path_bucket: PathBucket
		for path_bucket in aggs.method_path.buckets:
			datasets.append(self.get_histogram_chart(path_bucket, labels))

		if len(datasets) >= self.MAX_NO_OF_PATHS:
			datasets.append(self.get_other_bucket(datasets, labels))

		if self.normalize_slow_logs:
			datasets = normalize_datasets(datasets)

		labels = [label.replace(tzinfo=None) for label in labels]
		return {"datasets": datasets, "labels": labels}

	def run(self):
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if not log_server:
			return {"datasets": [], "labels": []}
		return self.get_stacked_histogram_chart()


class RequestGroupByChart(StackedGroupByChart):
	def __init__(self, name, agg_type, resource_type, timezone, timespan, timegrain):
		super().__init__(name, agg_type, resource_type, timezone, timespan, timegrain)

	def sum_of_duration(self):
		return A("sum", field="json.duration")

	def avg_of_duration(self):
		return A("avg", field="json.duration")

	def exclude_top_k_data(self, datasets):
		if ResourceType(self.resource_type) is ResourceType.SITE:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__request__path=path)
		elif ResourceType(self.resource_type) is ResourceType.SERVER:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__site=path)

	def setup_search_filters(self):
		super().setup_search_filters()
		self.search = self.search.filter("match_phrase", json__transaction_type="request").exclude(
			"match_phrase", json__request__path="/api/method/ping"
		)
		if ResourceType(self.resource_type) is ResourceType.SITE:
			self.search = self.search.filter("match_phrase", json__site=self.name)
			self.group_by_field = "json.request.path"
		elif ResourceType(self.resource_type) is ResourceType.SERVER:
			self.search = self.search.filter("match_phrase", agent__name=self.name)
			self.group_by_field = "json.site"


class BackgroundJobGroupByChart(StackedGroupByChart):
	def __init__(self, name, agg_type, resource_type, timezone, timespan, timegrain):
		super().__init__(name, agg_type, resource_type, timezone, timespan, timegrain)

	def sum_of_duration(self):
		return A("sum", field="json.duration")

	def avg_of_duration(self):
		return A("avg", field="json.duration")

	def exclude_top_k_data(self, datasets):
		if ResourceType(self.resource_type) is ResourceType.SITE:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__job__method=path)
		elif ResourceType(self.resource_type) is ResourceType.SERVER:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__site=path)

	def setup_search_filters(self):
		super().setup_search_filters()
		self.search = self.search.filter("match_phrase", json__transaction_type="job")
		if ResourceType(self.resource_type) is ResourceType.SITE:
			self.search = self.search.filter("match_phrase", json__site=self.name)
			self.group_by_field = "json.job.method"
		elif ResourceType(self.resource_type) is ResourceType.SERVER:
			self.search = self.search.filter("match_phrase", agent__name=self.name)
			self.group_by_field = "json.site"


class NginxRequestGroupBy(StackedGroupByChart):
	def __init__(self, name, agg_type, resource_type, timezone, timespan, timegrain):
		super().__init__(name, agg_type, resource_type, timezone, timespan, timegrain)

	def sum_of_duration(self):
		return A("sum", field="http.request.duration")

	def avg_of_duration(self):
		return A("avg", field="http.request.duration")

	def exclude_top_k_data(self, datasets):
		if ResourceType(self.resource_type) is ResourceType.SITE:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", source__ip=path)
		elif ResourceType(self.resource_type) is ResourceType.SERVER:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", http__request__site=path)

	def setup_search_filters(self):
		super().setup_search_filters()
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		if not (monitor_ip := press_settings.monitor_server):
			frappe.throw("Monitor server not set in Press Settings")
		self.search = self.search.exclude("match_phrase", source__ip=monitor_ip)
		if ResourceType(self.resource_type) is ResourceType.SITE:
			domains = frappe.get_all(
				"Site Domain",
				{"site": self.name},
				pluck="domain",
			)
			self.search = self.search.query(
				"bool", should=[{"match_phrase": {"http.request.site": domain}} for domain in domains]
			)
			self.group_by_field = "source.ip"
		elif ResourceType(self.resource_type) is ResourceType.SERVER:
			self.search = self.search.filter("match_phrase", agent__name=self.name)
			self.group_by_field = "http.request.site"


class SlowLogGroupByChart(StackedGroupByChart):
	to_s_divisor = 1e9
	database_name = None

	def __init__(
		self,
		name,
		agg_type,
		resource_type,
		timezone,
		timespan,
		timegrain,
		normalize_slow_logs=False,
	):
		super().__init__(name, agg_type, resource_type, timezone, timespan, timegrain)
		self.normalize_slow_logs = normalize_slow_logs

	def sum_of_duration(self):
		return A("sum", field="event.duration")

	def avg_of_duration(self):
		return A("avg", field="event.duration")

	def exclude_top_k_data(self, datasets):
		if ResourceType(self.resource_type) is ResourceType.SITE:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", mysql__slowlog__query=path)
		elif ResourceType(self.resource_type) is ResourceType.SERVER:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", mysql__slowlog__current_user=path)

	def setup_search_filters(self):
		super().setup_search_filters()
		self.search = self.search.exclude(
			"wildcard",
			mysql__slowlog__query="SELECT /\*!40001 SQL_NO_CACHE \*/*",  # noqa
		)
		if ResourceType(self.resource_type) is ResourceType.SITE:
			self.database_name = frappe.db.get_value("Site", self.name, "database_name")
			if self.database_name:
				self.search = self.search.filter("match", mysql__slowlog__current_user=self.database_name)
			self.group_by_field = "mysql.slowlog.query"
		elif ResourceType(self.resource_type) is ResourceType.SERVER:
			self.search = self.search.filter("match", agent__name=self.name)
			self.group_by_field = "mysql.slowlog.current_user"

	def run(self):
		if not self.database_name and ResourceType(self.resource_type) is ResourceType.SITE:
			return {"datasets": [], "labels": []}
		res = super().run()
		if ResourceType(self.resource_type) is not ResourceType.SERVER:
			return res
		for path_data in res["datasets"]:
			site_name = frappe.db.get_value(
				"Site",
				{
					"database_name": path_data["path"],
				},
				"name",
			)
			path_data["path"] = site_name or path_data["path"]

		return res


@frappe.whitelist()
@protected("Site")
@redis_cache(ttl=10 * 60)
def get(name, timezone, duration="7d"):
	timespan, timegrain = TIMESPAN_TIMEGRAIN_MAP[duration]

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
@redis_cache(ttl=10 * 60)
def get_advanced_analytics(name, timezone, duration="7d"):
	timespan, timegrain = TIMESPAN_TIMEGRAIN_MAP[duration]

	job_data = get_usage(name, "job", timezone, timespan, timegrain)

	return {
		"request_count_by_path": get_request_by_(name, "count", timezone, timespan, timegrain),
		"request_duration_by_path": get_request_by_(name, "duration", timezone, timespan, timegrain),
		"average_request_duration_by_path": get_request_by_(
			name, "average_duration", timezone, timespan, timegrain
		),
		"request_count_by_ip": get_nginx_request_by_(name, "count", timezone, timespan, timegrain),
		"background_job_count_by_method": get_background_job_by_method(
			name, "count", timezone, timespan, timegrain
		),
		"background_job_duration_by_method": get_background_job_by_method(
			name, "duration", timezone, timespan, timegrain
		),
		"average_background_job_duration_by_method": get_background_job_by_method(
			name, "average_duration", timezone, timespan, timegrain
		),
		"slow_logs_by_count": get_slow_logs(name, "count", timezone, timespan, timegrain),
		"slow_logs_by_duration": get_slow_logs(name, "duration", timezone, timespan, timegrain),
		"job_count": [{"value": r.count, "date": r.date} for r in job_data],
		"job_cpu_time": [{"value": r.duration, "date": r.date} for r in job_data],
	}


def get_more_request_detail_fn_names():
	return {
		"/api/method/run_doc_method": get_run_doc_method_methodnames.__name__,
		"/api/method/frappe.desk.query_report.run": get_query_report_run_reports.__name__,
	}


def get_more_background_job_detail_fn_names():
	return {
		"generate_report": get_generate_report_reports.__name__,
	}


@frappe.whitelist()
@protected("Site")
@redis_cache(ttl=10 * 60)
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


def get_request_by_(
	name, agg_type: AggType, timezone: str, timespan: int, timegrain: int, resource_type=ResourceType.SITE
):
	"""
	:param name: site/server name depending on resource_type
	:param agg_type: count, duration, average_duration
	:param timezone: timezone of timespan
	:param timespan: duration in seconds
	:param timegrain: interval in seconds
	:param resource_type: filter by site or server
	"""
	return RequestGroupByChart(name, agg_type, resource_type, timezone, timespan, timegrain).run()


def get_nginx_request_by_(name, agg_type: AggType, timezone: str, timespan: int, timegrain: int):
	return NginxRequestGroupBy(name, agg_type, ResourceType.SITE, timezone, timespan, timegrain).run()


def get_background_job_by_method(site, agg_type, timezone, timespan, timegrain):
	return BackgroundJobGroupByChart(site, agg_type, ResourceType.SITE, timezone, timespan, timegrain).run()


@frappe.whitelist()
def get_slow_logs_by_query(
	name: str, agg_type: str, timezone: str, duration: str = "24h", normalize: bool = False
):
	timespan, timegrain = TIMESPAN_TIMEGRAIN_MAP[duration]

	return get_slow_logs(name, agg_type, timezone, timespan, timegrain, ResourceType.SITE, normalize)


def get_slow_logs(
	name, agg_type, timezone, timespan, timegrain, resource_type=ResourceType.SITE, normalize=False
):
	return SlowLogGroupByChart(name, agg_type, resource_type, timezone, timespan, timegrain, normalize).run()


class RunDocMethodMethodNames(RequestGroupByChart):
	def __init__(self, name, agg_type, timezone, timespan, timegrain):
		super().__init__(name, agg_type, ResourceType.SITE, timezone, timespan, timegrain)
		self.group_by_field = "json.methodname"

	def setup_search_filters(self):
		super().setup_search_filters()
		self.search = self.search.filter("match_phrase", json__request__path="/api/method/run_doc_method")


def get_run_doc_method_methodnames(site, agg_type, timezone, timespan, timegrain):
	return RunDocMethodMethodNames(site, agg_type, timezone, timespan, timegrain).run()


class QueryReportRunReports(RequestGroupByChart):
	def __init__(self, name, agg_type, timezone, timespan, timegrain):
		super().__init__(name, agg_type, ResourceType.SITE, timezone, timespan, timegrain)
		self.group_by_field = "json.report"

	def setup_search_filters(self):
		super().setup_search_filters()
		self.search = self.search.filter(
			"match_phrase", json__request__path="/api/method/frappe.desk.query_report.run"
		)


def get_query_report_run_reports(site, agg_type, timezone, timespan, timegrain):
	return QueryReportRunReports(site, agg_type, timezone, timespan, timegrain).run()


class GenerateReportReports(BackgroundJobGroupByChart):
	def __init__(self, name, agg_type, timezone, timespan, timegrain):
		super().__init__(name, agg_type, ResourceType.SITE, timezone, timespan, timegrain)
		self.group_by_field = "json.report"

	def setup_search_filters(self):
		super().setup_search_filters()
		self.search = self.search.filter("match_phrase", json__job__method="generate_report")


def get_generate_report_reports(site, agg_type, timezone, timespan, timegrain):
	return GenerateReportReports(site, agg_type, timezone, timespan, timegrain).run()


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

	if not response.get("aggregations"):
		return {"datasets": [], "labels": []}

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
	agent = Agent(site.server)
	rows = agent.fetch_database_processes(site)
	for row in rows:
		row["state"] = row["state"].capitalize()
		row["query"] = sqlparse.format((row["query"] or "").strip(), keyword_case="upper", reindent=True)
	return rows


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
def deadlock_report(name, start_datetime, stop_datetime, max_log_size=500):
	from press.press.report.mariadb_deadlock_browser.mariadb_deadlock_browser import execute

	meta = frappe._dict(
		{
			"site": name,
			"start_datetime": start_datetime,
			"stop_datetime": stop_datetime,
			"max_log_size": max_log_size,
		}
	)
	_, data = execute(filters=meta)
	return data


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
	headers = {"Authorization": f"Bearer {settings.get_password('plausible_api_key')}"}

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
