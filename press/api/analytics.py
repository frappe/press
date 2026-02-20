# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import annotations

import math
from contextlib import suppress
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, Final, TypedDict

import frappe
import frappe.utils
import requests
import sqlparse
from elasticsearch import Elasticsearch
from elasticsearch_dsl import A, Search
from frappe import auth
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
from press.guards import site
from press.press.doctype.site_plan.site_plan import get_plan_config
from press.press.report.binary_log_browser.binary_log_browser import (
	get_data as get_binary_log_data,
)
from press.press.report.mariadb_slow_queries.mariadb_slow_queries import (
	execute,
	normalize_query,
)

if TYPE_CHECKING:
	from collections.abc import Callable

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

	class MetricType(TypedDict):
		date: str
		value: float


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

MAX_NO_OF_PATHS: Final[int] = 10
MAX_MAX_NO_OF_PATHS: Final[int] = 50

NICE_STEPS = [
	1,
	2,
	5,
	10,
	15,
	30,  # seconds
	60,
	90,
	120,
	300,
	600,
	900,
	1800,  # minutes: 1m,1.5m,2m,5m,10m,15m,30m
	3600,
	7200,
	14400,
	28800,  # hours: 1h,2h,4h,8h
	86400,
	604800,  # days, week
]


def auto_timespan_timegrain(start: datetime, end: datetime, target_points: int = 60):
	if end < start:
		raise ValueError("end must be >= start")

	total_seconds = int((end - start).total_seconds())

	if total_seconds <= 0:
		return (total_seconds, 0)

	no_of_intervals = max(1, target_points - 1)

	raw_interval = math.ceil(total_seconds / no_of_intervals)

	interval = next((step for step in NICE_STEPS if step >= raw_interval), raw_interval)

	return (total_seconds, interval)


class StackedGroupByChart:
	search: Search
	to_s_divisor: float = 1e6
	normalize_slow_logs: bool = False
	group_by_field: str
	max_no_of_paths: int = 10

	def __init__(
		self,
		name: str,
		agg_type: AggType,
		timezone: str,
		start: datetime,
		end: datetime,
		timespan: int,
		timegrain: int,
		resource_type: ResourceType,
		max_no_of_paths: int = MAX_NO_OF_PATHS,
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
		self.start = start
		self.end = end
		self.timegrain = timegrain
		self.max_no_of_paths = min(max_no_of_paths, MAX_MAX_NO_OF_PATHS)

		self.setup_search_filters()
		self.setup_search_aggs()

	def setup_search_filters(self):
		es = Elasticsearch(self.url, basic_auth=("frappe", self.password), request_timeout=120)
		self.start = get_rounded_boundary(self.start, self.timegrain)
		self.end = get_rounded_boundary(self.end, self.timegrain)

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
				size=self.max_no_of_paths,
				order={"path_count": "desc"},
			).bucket("histogram_of_method", self.histogram_of_method())
			self.search.aggs["method_path"].bucket("path_count", self.count_of_values())

		elif AggType(self.agg_type) is AggType.DURATION:
			self.search.aggs.bucket(
				"method_path",
				"terms",
				field=self.group_by_field,
				size=self.max_no_of_paths,
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
				size=self.max_no_of_paths,
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
			time_zone="UTC",
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
			"values": [None] * len(labels),
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
					else (hist_bucket.doc_count if AggType(self.agg_type) is AggType.COUNT else 0)
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

		if len(datasets) >= self.max_no_of_paths:
			datasets.append(self.get_other_bucket(datasets, labels))

		if self.normalize_slow_logs:
			datasets = normalize_datasets(datasets)

		labels = [convert_utc_to_timezone(label, self.timezone).replace(tzinfo=None) for label in labels]
		return {
			"datasets": datasets,
			"labels": labels,
			"allow_drill_down": self.allow_drill_down,
		}

	@property
	def allow_drill_down(self):
		if self.max_no_of_paths >= MAX_MAX_NO_OF_PATHS:
			return False
		return True

	def run(self):
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if not log_server:
			return {"datasets": [], "labels": []}
		return self.get_stacked_histogram_chart()


class RequestGroupByChart(StackedGroupByChart):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

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
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

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


class NginxRequestGroupByChart(StackedGroupByChart):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

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
		if not (
			press_settings.monitor_server
			and (
				monitor_ip := frappe.db.get_value(
					"Monitor Server", press_settings.monitor_server, "ip", cache=True
				)
			)
		):
			frappe.throw("Monitor server not set in Press Settings")
		self.search = self.search.exclude("match_phrase", source__ip=monitor_ip)
		if ResourceType(self.resource_type) is ResourceType.SITE:
			server = frappe.db.get_value("Site", self.name, "server")
			proxy = frappe.db.get_value("Server", server, "proxy_server")
			self.search = self.search.filter("match_phrase", agent__name=proxy)
			domains = frappe.get_all(
				"Site Domain",
				{"site": self.name},
				pluck="domain",
			)
			self.search = self.search.query(
				"bool",
				should=[{"match_phrase": {"http.request.site": domain}} for domain in domains],
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
		normalize_slow_logs=False,
		*args,
		**kwargs,
	):
		super().__init__(*args, **kwargs)
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


def _query_prometheus(query: dict[str, str]) -> dict[str, float | str]:
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	url = f"https://{monitor_server}/prometheus/api/v1/query_range"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")
	return requests.get(url, params=query, auth=("frappe", password)).json()


def _parse_datetime_in_metrics(timestamp: float, timezone: str) -> str:
	return str(datetime.fromtimestamp(timestamp, tz=pytz_timezone(timezone)))


def _get_cadvisor_data(promql_query: str, timezone: str, timespan: int, timegrain: int):
	end = datetime.now(pytz_timezone(timezone))
	start = frappe.utils.add_to_date(end, seconds=-timespan)
	datasets = []
	labels = []

	query = {
		"query": promql_query,
		"start": start.timestamp(),
		"end": end.timestamp(),
		"step": f"{timegrain}s",
	}

	result = _query_prometheus(query)["data"]["result"]

	if not result:
		return None

	for res in result:
		datasets.append(
			{
				"name": res["metric"]["name"],
				"values": [float(value[1]) for value in res["values"]],
			}
		)

	for metric in res["values"]:
		labels.append(_parse_datetime_in_metrics(metric[0], timezone))

	return datasets, labels


def get_metrics(
	promql_query: str,
	timezone: str,
	response_key: str,
	name: str | None = None,
	duration: str = "24h",
):
	if not name:
		frappe.throw("No release group found!")

	benches = frappe.get_all("Bench", {"status": "Active", "group": name}, pluck="name")

	if not benches:
		frappe.throw("No active benches found!")

	benches = "|".join(benches)
	timespan, timegrain = TIMESPAN_TIMEGRAIN_MAP[duration]

	try:
		promql_query = promql_query.format(benches=benches)
		datasets, labels = _get_cadvisor_data(promql_query, timezone, timespan, timegrain)
		return {response_key: {"datasets": datasets, "labels": labels}}
	except ValueError:
		frappe.throw("Unable to fetch metrics")


@frappe.whitelist()
@protected("Release Group")
def get_fs_read_bytes(name: str, timezone: str, duration: str = "24h"):
	promql_query = (
		'sum by (name) (rate(container_fs_reads_bytes_total{{job="cadvisor", name=~"{benches}"}}[5m]))'
	)
	return get_metrics(
		promql_query=promql_query,
		timezone=timezone,
		response_key="read_bytes_fs",
		name=name,
		duration=duration,
	)


@frappe.whitelist()
@protected("Release Group")
def get_fs_write_bytes(name: str, timezone: str, duration: str = "24h"):
	promql_query = (
		'sum by (name) (rate(container_fs_writes_bytes_total{{job="cadvisor", name=~"{benches}"}}[5m]))'
	)
	return get_metrics(
		promql_query=promql_query,
		timezone=timezone,
		response_key="write_bytes_fs",
		name=name,
		duration=duration,
	)


@frappe.whitelist()
@protected("Release Group")
def get_outgoing_network_traffic(name: str, timezone: str, duration: str = "24h"):
	promql_query = 'sum by (name) (rate(container_network_transmit_bytes_total{{job="cadvisor", name=~"{benches}"}}[5m]))'
	return get_metrics(
		promql_query=promql_query,
		timezone=timezone,
		response_key="network_traffic_outward",
		name=name,
		duration=duration,
	)


@frappe.whitelist()
@protected("Release Group")
def get_incoming_network_traffic(name: str, timezone: str, duration: str = "24h"):
	promql_query = (
		'sum by (name) (rate(container_network_receive_bytes_total{{job="cadvisor", name=~"{benches}"}}[5m]))'
	)
	return get_metrics(
		promql_query=promql_query,
		timezone=timezone,
		response_key="network_traffic_inward",
		name=name,
		duration=duration,
	)


@frappe.whitelist()
@protected("Release Group")
def get_memory_usage(name: str, timezone: str, duration: str = "24h"):
	promql_query = 'sum by (name) (avg_over_time(container_memory_usage_bytes{{job="cadvisor", name=~"{benches}"}}[5m]) / 1024 / 1024 / 1024)'
	return get_metrics(
		promql_query=promql_query,
		timezone=timezone,
		response_key="memory",
		name=name,
		duration=duration,
	)


@frappe.whitelist()
@protected("Release Group")
def get_cpu_usage(name: str, timezone: str, duration: str = "24h"):
	promql_query = (
		'sum by (name) ( rate(container_cpu_usage_seconds_total{{job="cadvisor", name=~"{benches}"}}[5m]))'
	)
	return get_metrics(
		promql_query=promql_query,
		timezone=timezone,
		response_key="cpu",
		name=name,
		duration=duration,
	)


@frappe.whitelist()
@protected("Site")
@redis_cache(ttl=15 * 60)
def get(name, timezone, start, end):
	start = datetime.fromisoformat(start.replace("Z", "+00:00"))
	end = datetime.fromisoformat(end.replace("Z", "+00:00"))
	_, timegrain = auto_timespan_timegrain(start, end)

	request_data = get_usage(name, "request", timezone, start, end, timegrain)
	uptime_data = get_uptime(name, timezone, start, end, timegrain)

	plan = frappe.get_cached_doc("Site", name).plan
	plan_limit = get_plan_config(plan).get("rate_limit", {}).get("limit") if plan else 0

	return {
		"usage_counter": [{"value": r.max, "date": r.date} for r in request_data],
		"request_count": [{"value": r.count, "date": r.date} for r in request_data],
		"request_cpu_time": [{"value": r.duration, "date": r.date} for r in request_data],
		"uptime": uptime_data,
		"plan_limit": plan_limit,
	}


def add_commonly_slow_path_to_reports(
	reports: dict, path: str, name: str, timezone, start, end, timespan, timegrain, max_no_of_paths
):
	for slow_path in COMMONLY_SLOW_PATHS + COMMONLY_SLOW_JOBS:
		if slow_path["path"] == path:
			reports[slow_path["id"]] = slow_path["function"](
				name,
				"duration",
				timezone,
				start,
				end,
				timespan,
				timegrain,
				ResourceType.SITE,
				max_no_of_paths,
			)
			break


def get_additional_duration_reports(
	request_duration_by_path, name: str, timezone, start, end, timespan, timegrain, max_no_of_paths
):
	"""Get additional reports for the request duration by path"""
	reports = {}
	for path_data in request_duration_by_path["datasets"][:4]:  # top 4 paths
		add_commonly_slow_path_to_reports(
			reports,
			path_data["path"],
			name,
			timezone,
			start,
			end,
			timespan,
			timegrain,
			max_no_of_paths,
		)

	return reports


@frappe.whitelist()
def get_advanced_analytics(name, timezone, start, end, max_no_of_paths=MAX_NO_OF_PATHS):
	start = datetime.fromisoformat(start.replace("Z", "+00:00"))
	end = datetime.fromisoformat(end.replace("Z", "+00:00"))
	timespan, timegrain = auto_timespan_timegrain(start, end)

	job_data = get_usage(name, "job", timezone, start, end, timegrain)

	request_duration_by_path = get_request_by_(
		name,
		"duration",
		timezone,
		start,
		end,
		timespan,
		timegrain,
		ResourceType.SITE,
		max_no_of_paths,
	)

	background_job_duration_by_method = get_background_job_by_(
		name,
		"duration",
		timezone,
		start,
		end,
		timespan,
		timegrain,
		ResourceType.SITE,
		max_no_of_paths,
	)

	return (
		{
			"request_count_by_path": get_request_by_(
				name,
				"count",
				timezone,
				start,
				end,
				timespan,
				timegrain,
				ResourceType.SITE,
				max_no_of_paths,
			),
			"request_duration_by_path": request_duration_by_path,
			"average_request_duration_by_path": get_request_by_(
				name,
				"average_duration",
				timezone,
				start,
				end,
				timespan,
				timegrain,
				ResourceType.SITE,
				max_no_of_paths,
			),
			"request_count_by_ip": get_nginx_request_by_(
				name, "count", timezone, start, end, timespan, timegrain, max_no_of_paths
			),
			"background_job_count_by_method": get_background_job_by_(
				name,
				"count",
				timezone,
				start,
				end,
				timespan,
				timegrain,
				ResourceType.SITE,
				max_no_of_paths,
			),
			"background_job_duration_by_method": background_job_duration_by_method,
			"average_background_job_duration_by_method": get_background_job_by_(
				name,
				"average_duration",
				timezone,
				start,
				end,
				timespan,
				timegrain,
				ResourceType.SITE,
				max_no_of_paths,
			),
			"job_count": [{"value": r.count, "date": r.date} for r in job_data],
			"job_cpu_time": [{"value": r.duration, "date": r.date} for r in job_data],
		}
		| get_additional_duration_reports(
			request_duration_by_path,
			name,
			timezone,
			start,
			end,
			timespan,
			timegrain,
			max_no_of_paths,
		)
		| get_additional_duration_reports(
			background_job_duration_by_method,
			name,
			timezone,
			start,
			end,
			timespan,
			timegrain,
			max_no_of_paths,
		)
	)


@frappe.whitelist()
@protected("Site")
@redis_cache(ttl=15 * 60)
def daily_usage(name, timezone):
	timespan = 7 * 24 * 60 * 60
	timegrain = 24 * 60 * 60

	end = datetime.now(pytz_timezone(timezone))
	start = frappe.utils.add_to_date(end, seconds=-timespan)

	request_data = get_usage(
		name,
		"request",
		timezone,
		start,
		end,
		timegrain,
	)

	plan = frappe.get_cached_doc("Site", name).plan

	return {
		"data": [{"value": r.max, "date": r.date} for r in request_data],
		"plan_limit": get_plan_config(plan)["rate_limit"]["limit"] if plan else 0,
	}


def rounded_time(dt: datetime | None = None, round_to=60):
	"""Round a datetime object to any time lapse in seconds
	dt : datetime.datetime object, default now.
	round_to : Closest number of seconds to round to, default 1 minute.
	ref: https://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object/10854034#10854034
	"""
	if dt is None:
		dt = datetime.now()
	seconds = (dt.replace(tzinfo=None) - dt.min).seconds
	rounding = (seconds + round_to / 2) // round_to * round_to
	return dt + timedelta(0, rounding - seconds, -dt.microsecond)


@redis_cache(ttl=15 * 60)
def get_rounded_boundaries(timespan: int, timegrain: int, timezone: str = "UTC"):
	"""
	Round the start and end time to the nearest interval, because Elasticsearch does this
	"""
	end = datetime.now(pytz_timezone(timezone))
	start = frappe.utils.add_to_date(end, seconds=-timespan)

	return rounded_time(start, timegrain), rounded_time(end, timegrain)


@redis_cache(ttl=15 * 60)
def get_rounded_boundary(dt: datetime, timegrain=60):
	"""
	Floor a datetime to the previous interval boundary.

	Args:
		dt: datetime instance
		timegrain: timegrain in seconds

	Returns:
		datetime floored to the timegrain interval boundary
	"""
	if timegrain <= 0:
		raise ValueError("timegrain must be positive")

	ts = dt.timestamp()
	floored_ts = ts - (ts % timegrain)

	return datetime.fromtimestamp(floored_ts, tz=dt.tzinfo)


def get_uptime(site, timezone, start: datetime, end: datetime, _):
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		return []

	url = f"https://{monitor_server}/prometheus/api/v1/query_range"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")

	# align to beginning of day of start date
	start = start.astimezone(pytz_timezone(timezone)).replace(hour=0, minute=0, second=0, microsecond=0)
	# align to end of day of end date
	end = end.astimezone(pytz_timezone(timezone)).replace(
		hour=0, minute=0, second=0, microsecond=0
	) + timedelta(days=1)

	timegrain = 86400  # 1 day

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
				x + y for x, y in zip(n_datasets[n_query]["values"], data_dict["values"], strict=False)
			]
		else:
			data_dict["path"] = n_query
			n_datasets[n_query] = data_dict
	return list(n_datasets.values())


@redis_cache(ttl=15 * 60)
def get_request_by_(
	name,
	agg_type: AggType,
	timezone: str,
	start: datetime,
	end: datetime,
	timespan: int,
	timegrain: int,
	resource_type=ResourceType.SITE,
	max_no_of_paths=MAX_NO_OF_PATHS,
):
	"""
	:param name: site/server name depending on resource_type
	:param agg_type: count, duration, average_duration
	:param timezone: timezone of timespan
	:param timespan: duration in seconds
	:param timegrain: interval in seconds
	:param resource_type: filter by site or server
	"""
	return RequestGroupByChart(
		name, agg_type, timezone, start, end, timespan, timegrain, resource_type, max_no_of_paths
	).run()


@redis_cache(ttl=15 * 60)
def get_nginx_request_by_(
	name,
	agg_type: AggType,
	timezone: str,
	start: datetime,
	end: datetime,
	timespan: int,
	timegrain: int,
	max_no_of_paths,
):
	return NginxRequestGroupByChart(
		name,
		agg_type,
		timezone,
		start,
		end,
		timespan,
		timegrain,
		ResourceType.SITE,
		max_no_of_paths,
	).run()


@redis_cache(ttl=15 * 60)
def get_background_job_by_(
	site,
	agg_type,
	timezone,
	start,
	end,
	timespan,
	timegrain,
	resource_type=ResourceType.SITE,
	max_no_of_paths=MAX_NO_OF_PATHS,
):
	return BackgroundJobGroupByChart(
		site, agg_type, timezone, start, end, timespan, timegrain, resource_type, max_no_of_paths
	).run()


@frappe.whitelist()
def get_slow_logs_by_query(
	name: str,
	agg_type: str,
	timezone: str,
	start: str | datetime,
	end: str | datetime,
	normalize: bool = False,
	max_no_of_paths: int = MAX_NO_OF_PATHS,
):
	start = datetime.fromisoformat(start.replace("Z", "+00:00"))
	end = datetime.fromisoformat(end.replace("Z", "+00:00"))
	timespan, timegrain = auto_timespan_timegrain(start, end)

	return get_slow_logs(
		name,
		agg_type,
		timezone,
		start,
		end,
		timespan,
		timegrain,
		ResourceType.SITE,
		normalize,
		max_no_of_paths,
	)


@redis_cache(ttl=15 * 60)
def get_slow_logs(
	name,
	agg_type,
	timezone,
	start,
	end,
	timespan,
	timegrain,
	resource_type=ResourceType.SITE,
	normalize=False,
	max_no_of_paths=MAX_NO_OF_PATHS,
):
	return SlowLogGroupByChart(
		normalize,
		name,
		agg_type,
		timezone,
		start,
		end,
		timespan,
		timegrain,
		resource_type,
		max_no_of_paths,
	).run()


class RunDocMethodMethodNames(RequestGroupByChart):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def setup_search_filters(self):
		super().setup_search_filters()
		self.group_by_field = "json.methodname"
		self.search = self.search.filter("match_phrase", json__request__path="/api/method/run_doc_method")

	def exclude_top_k_data(self, datasets: list[Dataset]):
		if ResourceType(self.resource_type) is ResourceType.SITE:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__methodname=path)
		elif ResourceType(self.resource_type) is ResourceType.SERVER:  # not used atp
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__site=path)


def get_run_doc_method_methodnames(*args, **kwargs):
	return RunDocMethodMethodNames(*args, **kwargs).run()


class QueryReportRunReports(RequestGroupByChart):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def setup_search_filters(self):
		super().setup_search_filters()
		self.group_by_field = "json.report"
		self.search = self.search.filter(
			"match_phrase",
			json__request__path="/api/method/frappe.desk.query_report.run",
		)

	def exclude_top_k_data(self, datasets: list[Dataset]):
		if ResourceType(self.resource_type) is ResourceType.SITE:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__report=path)
		elif ResourceType(self.resource_type) is ResourceType.SERVER:  # not used atp
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__site=path)


def get_query_report_run_reports(*args, **kwargs):
	return QueryReportRunReports(*args, **kwargs).run()


def get_generate_report_reports(*args, **kwargs):
	return GenerateReportReports(*args, **kwargs).run()


class CommonSlowPath(TypedDict):
	path: str
	id: str
	function: Callable


COMMONLY_SLOW_PATHS: list[CommonSlowPath] = [
	{
		"path": "/api/method/run_doc_method",
		"id": "run_doc_method_methodnames",
		"function": get_run_doc_method_methodnames,
	},
	{
		"path": "/api/method/frappe.desk.query_report.run",
		"id": "query_report_run_reports",
		"function": get_query_report_run_reports,
	},
]

COMMONLY_SLOW_JOBS: list[CommonSlowPath] = [
	{
		"path": "generate_report",
		"id": "generate_report_reports",
		"function": get_generate_report_reports,
	},
	{
		"path": "frappe.core.doctype.prepared_report.prepared_report.generate_report",
		"id": "generate_report_reports",
		"function": get_generate_report_reports,
	},
]


class GenerateReportReports(BackgroundJobGroupByChart):
	paths: ClassVar = [job["path"] for job in COMMONLY_SLOW_JOBS if job["id"] == "generate_report_reports"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def setup_search_filters(self):
		super().setup_search_filters()
		self.group_by_field = "json.report"
		self.search = self.search.query(
			"bool",
			should=[{"match_phrase": {"json.job.method": path}} for path in self.paths],
		)

	def exclude_top_k_data(self, datasets: list[Dataset]):
		if ResourceType(self.resource_type) is ResourceType.SITE:
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__report=path)
		elif ResourceType(self.resource_type) is ResourceType.SERVER:  # not used atp
			for path in list(map(lambda x: x["path"], datasets)):
				self.search = self.search.exclude("match_phrase", json__site=path)


def get_usage(site, type, timezone, start, end, timegrain):
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
					{
						"range": {
							"@timestamp": {
								"gte": int(start.timestamp() * 1000),
								"lte": int(end.timestamp() * 1000),
							}
						}
					},
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
@site.feature("monitor_access")
def request_logs(site, timezone, date, sort=None, start=0):
	result = []
	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		frappe.log_error("Log server not configured")
		return result

	url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
	try:
		password = auth.get_decrypted_password("Log Server", log_server, "kibana_password")
	except Exception as e:
		frappe.log_error(f"Failed to get log server password: {e}")
		return []

	sort_options = {
		"Time (Ascending)": {"@timestamp": "asc"},
		"Time (Descending)": {"@timestamp": "desc"},
		"CPU Time (Descending)": {"json.duration": "desc"},
	}
	sort_value = sort_options.get(sort, sort_options["CPU Time (Descending)"])

	query = {
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.transaction_type": "request"}},
					{"match_phrase": {"json.site": site}},
					{"range": {"@timestamp": {"gt": f"{date}||-1d/d", "lte": f"{date}||/d"}}},
				],
				"must_not": [{"match_phrase": {"json.request.path": "/api/method/ping"}}],
			}
		},
		"sort": sort_value,
		"from": start,
		"size": 10,
	}

	try:
		response = requests.post(url, json=query, auth=("frappe", password), timeout=10)
		response.raise_for_status()
		data_json = response.json()
	except requests.RequestException as e:
		frappe.log_error(f"Log server request failed: {e}")
		return result
	except ValueError as e:
		frappe.log_error(f"Invalid JSON response: {e}")
		return result

	for hit in data_json.get("hits", {}).get("hits", []):
		data = hit.get("_source", {}).get("json", {})
		if not data:
			continue
		try:
			data["timestamp"] = convert_utc_to_timezone(
				frappe.utils.get_datetime(data["timestamp"]).replace(tzinfo=None),
				timezone,
			)
		except Exception as e:
			frappe.log_error(f"Timestamp conversion failed: {e}")
			data["timestamp"] = None
		result.append(data)

	return result


@frappe.whitelist()
@protected("Site")
@site.feature("monitor_access")
def binary_logs(site, start_time, end_time, pattern: str = ".*", max_lines: int = 4000):
	filters = frappe._dict(
		site=site,
		database=frappe.db.get_value("Site", site, "database_name"),
		start_datetime=start_time,
		stop_datetime=end_time,
		pattern=pattern,
		max_lines=max_lines,
	)

	return get_binary_log_data(filters)


@frappe.whitelist()
@protected("Site")
@site.feature("monitor_access")
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
@site.feature("monitor_access")
def mariadb_slow_queries(
	site,
	start_datetime,
	stop_datetime,
	max_lines=1000,
	search_pattern=".*",
	normalize_queries=True,
	analyze=False,
):
	meta = frappe._dict(
		{
			"site": site,
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
@site.feature("monitor_access")
def deadlock_report(site, start_datetime, stop_datetime, max_log_size=500):
	from press.press.report.mariadb_deadlock_browser.mariadb_deadlock_browser import (
		execute,
	)

	meta = frappe._dict(
		{
			"site": site,
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
