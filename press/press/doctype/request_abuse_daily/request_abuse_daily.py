# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_system_timezone, getdate, nowdate

from press.mcp.tools.telemetry.clients import elasticsearch_post
from press.utils import log_error

MAX_SITES = 500
TOP_IPS = 20
# The site is the Host header the client sent, so only a plain host name that fits the Data field is kept
HOST_NAME = re.compile(r"^[a-z0-9.-]{1,140}$", re.IGNORECASE)


class RequestAbuseDaily(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.request_abuse_daily_ip.request_abuse_daily_ip import RequestAbuseDailyIP

		date: DF.Date
		forbidden: DF.Int
		rate_limited: DF.Int
		requests: DF.Int
		server_errors: DF.Int
		site: DF.Data
		top_ips: DF.Table[RequestAbuseDailyIP]
		unauthorized: DF.Int
		unique_ips: DF.Int
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days: int = 90):
		cutoff = add_days(nowdate(), -days)
		summaries = frappe.qb.DocType("Request Abuse Daily")
		ips = frappe.qb.DocType("Request Abuse Daily IP")
		expired = frappe.qb.from_(summaries).select(summaries.name).where(summaries.date < cutoff)
		(
			frappe.qb.from_(ips)
			.delete()
			.where(ips.parent.isin(expired))
			.where(ips.parenttype == "Request Abuse Daily")
		).run()
		frappe.db.delete("Request Abuse Daily", {"date": ("<", cutoff)})

	def record(self, response: dict):
		"""Fill the counters from one day of nginx logs of the site."""
		statuses = status_counts(response)
		self.requests = response["hits"]["total"]["value"]
		self.rate_limited = statuses.get(429, 0)
		self.unauthorized = statuses.get(401, 0)
		self.forbidden = statuses.get(403, 0)
		self.server_errors = sum(count for status, count in statuses.items() if status >= 500)
		self.unique_ips = response["aggregations"]["unique_ips"]["value"]
		self.top_ips = []
		for bucket in response["aggregations"]["rate_limited"]["ips"]["buckets"]:
			self.append("top_ips", {"ip": bucket["key"], "rate_limited": bucket["doc_count"]})


def record_yesterday():
	"""Summarise yesterday's rate limiting, auth failures and errors per site from the nginx logs."""
	if not frappe.db.get_single_value("Press Settings", "log_server"):
		return
	record_day(add_days(nowdate(), -1))


def record_day(date):
	start, end = day_bounds_in_milliseconds(date)
	for site in sites_to_summarise(start, end):
		frappe.db.savepoint("request_abuse_daily")
		try:
			record_site(date, site, start, end)
		except Exception:
			# Nothing re-runs yesterday, so one bad site must not cost the day for the rest
			frappe.db.rollback(save_point="request_abuse_daily")
			log_error("Request Abuse Summary Exception", date=date, site=site)


def record_site(date, site: str, start: int, end: int):
	summary = get_summary(date, site)
	summary.record(elasticsearch_post(site_day_query(site, start, end), should_redact=False))
	summary.save()


def sites_to_summarise(start: int, end: int) -> list[str]:
	"""Every site that was rate limited that day, and Press itself."""
	response = elasticsearch_post(rate_limited_sites_query(start, end), should_redact=False)
	sites = [bucket["key"] for bucket in response["aggregations"]["sites"]["buckets"]]
	return sorted({site for site in sites if HOST_NAME.match(site)} | {frappe.local.site})


def get_summary(date, site: str) -> RequestAbuseDaily:
	name = frappe.db.exists("Request Abuse Daily", {"date": date, "site": site})
	if name:
		return RequestAbuseDaily("Request Abuse Daily", name)
	return RequestAbuseDaily({"doctype": "Request Abuse Daily", "date": date, "site": site})


def day_bounds_in_milliseconds(date) -> tuple[int, int]:
	"""Start and end of the day in the system timezone, as epoch milliseconds for @timestamp."""
	day = getdate(date) if date else None
	if not day:
		raise frappe.ValidationError("A date is required to summarise the request logs")
	start = datetime.combine(day, time.min, tzinfo=ZoneInfo(get_system_timezone()))
	end = start + timedelta(days=1)
	return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def rate_limited_sites_query(start: int, end: int) -> dict:
	return {
		"size": 0,
		"query": {"bool": {"filter": [time_range(start, end), {"term": {"http.response.status_code": 429}}]}},
		"aggs": {"sites": {"terms": {"field": "http.request.site", "size": MAX_SITES}}},
	}


def site_day_query(site: str, start: int, end: int) -> dict:
	return {
		"size": 0,
		"track_total_hits": True,
		"query": {
			"bool": {"filter": [time_range(start, end), {"match_phrase": {"http.request.site": site}}]}
		},
		"aggs": {
			"status": {"terms": {"field": "http.response.status_code", "size": 50}},
			"unique_ips": {"cardinality": {"field": "source.ip"}},
			"rate_limited": {
				"filter": {"term": {"http.response.status_code": 429}},
				"aggs": {"ips": {"terms": {"field": "source.ip", "size": TOP_IPS}}},
			},
		},
	}


def time_range(start: int, end: int) -> dict:
	return {"range": {"@timestamp": {"gte": start, "lt": end}}}


def status_counts(response: dict) -> dict[int, int]:
	buckets = response["aggregations"]["status"]["buckets"]
	return {int(bucket["key"]): bucket["doc_count"] for bucket in buckets}
