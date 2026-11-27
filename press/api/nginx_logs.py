# Copyright (c) 2026, Frappe and Contributors
# See license.txt
"""Proxy nginx access log lines of one site, read from the log server."""

from __future__ import annotations

from typing import Final

import frappe
from elasticsearch import Elasticsearch
from frappe.utils import convert_utc_to_timezone, get_datetime, getdate
from frappe.utils.password import get_decrypted_password

from press.api.site import protected
from press.guards import site

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


@frappe.whitelist()
@protected("Site")
@site.feature("monitor_access", site_key="name")
def get(name: str, timezone: str, date: str, status: str = "All") -> list[dict]:
	query = site_query(name)
	query["bool"]["filter"] += [
		{"range": {"@timestamp": day_range(date, timezone)}},
		{"range": {"http.response.status_code": {"gte": MINIMUM_STATUS[status]}}},
	]
	response = log_server_client().search(
		index="filebeat-*", query=query, sort=[{"@timestamp": "desc"}], size=LIMIT, source=FIELDS
	)
	return [to_row(hit["_source"], timezone) for hit in response["hits"]["hits"]]


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


def day_range(date: str, timezone: str) -> dict:
	day = getdate(date).isoformat()
	return {"gte": day, "lt": f"{day}||+1d", "time_zone": timezone}


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
