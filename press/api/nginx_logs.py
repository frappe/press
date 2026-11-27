# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""Proxy nginx access log lines of one site, read from the log server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import frappe
from elasticsearch import Elasticsearch
from frappe.utils import convert_utc_to_timezone, get_datetime
from frappe.utils.password import get_decrypted_password

from press.api.analytics import auto_timespan_timegrain, parse_iso_datetime
from press.api.site import protected
from press.guards import site

if TYPE_CHECKING:
	from datetime import datetime

LIMIT: Final[int] = 200
MINIMUM_STATUS: Final[dict[str, int]] = {"All": 0, "Errors (4xx, 5xx)": 400, "Server Errors (5xx)": 500}
# No url.query: login and password reset links carry keys in it
FIELDS: Final[list[str]] = [
	"@timestamp",
	"http.request.method",
	"url.path",
	"http.response.status_code",
	"http.request.duration",
	"source.ip",
]


STATUS_CLASSES: Final[list[dict]] = [
	{"key": "2xx, 3xx", "to": 400},
	{"key": "4xx", "from": 400, "to": 500},
	{"key": "5xx", "from": 500},
]


@frappe.whitelist()
@protected("Site")
@site.feature("monitor_access", site_key="name")
def get(name: str, timezone: str, start: str, end: str, status: str = "All") -> dict:
	start_time, end_time = parse_iso_datetime(start), parse_iso_datetime(end)
	query = site_query(name)
	query["bool"]["filter"] += [
		{"range": {"@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}},
		{"range": {"http.response.status_code": {"gte": MINIMUM_STATUS[status]}}},
	]
	response = log_server_client().search(
		index="filebeat-*",
		query=query,
		sort=[{"@timestamp": "desc"}],
		size=LIMIT,
		source=FIELDS,
		aggs={"histogram": histogram_aggregation(start_time, end_time, timezone)},
	)
	return {
		"rows": [to_row(hit["_source"], timezone) for hit in response["hits"]["hits"]],
		"histogram": to_histogram(response["aggregations"]["histogram"]["buckets"]),
	}


def histogram_aggregation(start: datetime, end: datetime, timezone: str) -> dict:
	"""Request counts in about 60 buckets, split by status class, labelled in the viewer's timezone."""
	_, interval = auto_timespan_timegrain(start, end)
	return {
		"date_histogram": {
			"field": "@timestamp",
			"fixed_interval": f"{max(interval, 1)}s",
			"time_zone": timezone,
			"format": "yyyy-MM-dd HH:mm:ss",
			"min_doc_count": 0,
			"extended_bounds": {"min": start.isoformat(), "max": end.isoformat()},
		},
		"aggs": {"status": {"range": {"field": "http.response.status_code", "ranges": STATUS_CLASSES}}},
	}


def to_histogram(buckets: list[dict]) -> dict:
	"""Shape the buckets for the dashboard BarChart: one stacked dataset per status class."""
	return {
		"labels": [bucket["key_as_string"] for bucket in buckets],
		"datasets": [
			{
				"path": status_class["key"],
				"stack": "status",
				"values": [bucket["status"]["buckets"][index]["doc_count"] for bucket in buckets],
			}
			for index, status_class in enumerate(STATUS_CLASSES)
		],
	}


def site_query(site_name: str) -> dict:
	"""Match the lines of this site on its proxy, and never the lines of a neighbor site."""
	server = frappe.db.get_value("Site", site_name, "server")
	proxy = frappe.db.get_value("Server", server, "proxy_server")
	domains = {site_name, *frappe.get_all("Site Domain", {"site": site_name}, pluck="domain")}
	return {
		"bool": {
			"filter": [{"term": {"agent.name": proxy}}],
			"should": [{"term": {"http.request.site": domain}} for domain in sorted(domains)],
			"minimum_should_match": 1,
		}
	}


def log_server_client() -> Elasticsearch:
	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	password = get_decrypted_password("Log Server", log_server, "kibana_password")
	return Elasticsearch(
		f"https://{log_server}/elasticsearch", basic_auth=("frappe", password), request_timeout=30
	)


def to_row(source: dict, timezone: str) -> dict:
	http = source.get("http", {})
	timestamp = get_datetime(source["@timestamp"]).replace(tzinfo=None)
	return {
		"timestamp": convert_utc_to_timezone(timestamp, timezone),
		"method": http.get("request", {}).get("method"),
		"path": source.get("url", {}).get("path"),
		"status": http.get("response", {}).get("status_code"),
		"duration": http.get("request", {}).get("duration"),
		"ip": source.get("source", {}).get("ip"),
	}
