# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
"""Guest endpoint for Agent → Press WAF log ingestion.

Mirrors `press.api.monitoring.alert` (Alertmanager webhook): the inbound
payload authenticates with a per-site bearer token stored on the `WAF`
doctype as `waf_log_token`, after which we set the session to Administrator
and bulk-insert `WAF Log` rows. Press never polls; the Agent's
`waf_log_watcher` process drives everything from here (see
`agent/agent/waf_log_watcher.py`).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
from frappe.utils.password import get_decrypted_password

from press.utils import log_error

if TYPE_CHECKING:
	from typing import Any


# Per-far-endpoint rate limit. The real mover is the small flush batches
# the watcher emits, but a runaway agent shouldn't be able to drown Press.
INGEST_RATE_LIMIT = 60  # requests per minute per IP


def _server_ips_for_waf() -> set[str]:
	"""Return server IPs known to run the WAF watcher.

	Used purely to relax the rate limit for legitimate agents, mirroring
	`get_monitor_server_ips` in `press.api.monitoring` — auth still happens
	via the per-site bearer token, so relaxing the limit doesn't widen the
	trust boundary.
	"""
	server_types = ("Server", "Proxy Server", "Database Server")
	ips: set[str] = set()
	for doctype in server_types:
		rows = frappe.get_all(doctype, {"status": ("!=", "Archived")}, ["ip", "private_ip"])
		for row in rows:
			for attr in ("ip", "private_ip"):
				value = row.get(attr)
				if value:
					ips.add(value)
	return ips


def _ingest_rate_limit() -> int:
	if (
		frappe.local
		and hasattr(frappe.local, "request_ip")
		and frappe.local.request_ip in _server_ips_for_waf()
	):
		return 600  # no practical ceiling for known agents
	return INGEST_RATE_LIMIT


@frappe.whitelist(allow_guest=True)
def ingest_logs():
	"""Receive a batch of WAF audit events from an Agent.

	Contract:
		Header: X-WAF-Token: <waf_log_token>
		Header: X-Press-Site: <site name>
		Body:   JSON array of event dicts (see WAF Log doctype fields)

	Returns ``{"inserted": n, "duplicates": m}``. Duplicates — judged by
	``transaction_id`` which ModSecurity guarantees unique per transaction —
	are silently skipped so the Agent's at-least-once retry doesn't double-up.
	"""
	token = frappe.get_request_header("X-WAF-Token", "").strip()
	if not token:
		log_error("Missing WAF token")
		frappe.throw_permission_error()
	site = frappe.get_request_header("X-Press-Site", "").strip()
	if not site:
		frappe.throw_permission_error()

	if not _authenticate(site, token):
		# match_user stays anonymous → frappe logs far-end IP in error log
		log_error("WAF Ingest Auth Failure", site=site)
		frappe.throw_permission_error()

	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		payload = json.loads(frappe.request.get_data(as_text=True) or "[]")
		server = _site_server(site)
		inserted = 0
		duplicates = 0
		for event in payload:
			tid = (event.get("transaction_id") or "").strip()
			if not tid:
				continue
			if frappe.db.exists("WAF Log", {"transaction_id": tid}):
				duplicates += 1
				continue
			doc = frappe.get_doc(
				{
					"doctype": "WAF Log",
					"transaction_id": tid,
					"timestamp": _coerce_timestamp(event.get("timestamp")),
					"site": site,
					"server": server,
					"client_ip": event.get("client_ip"),
					"request_method": event.get("request_method"),
					"request_uri": event.get("request_uri"),
					"rule_id": event.get("rule_id"),
					"rule_msg": event.get("rule_msg"),
					"severity": _coerce_severity(event.get("severity")),
					"action": _coerce_action(event.get("action")),
					"matched_data": _coerce_truncated(event.get("matched_data"), 4_000),
					"raw_log": _coerce_truncated(event.get("raw_log"), 16_000),
				}
			)
			doc.insert(ignore_permissions=True, set_name=tid)
			inserted += 1
		frappe.db.commit()
		return {"inserted": inserted, "duplicates": duplicates}
	except Exception:
		frappe.db.rollback()
		log_error("WAF Ingest Failure")
		raise
	finally:
		frappe.set_user(previous_user)


def _authenticate(site: str, token: str) -> bool:
	"""Resolve the WAF doc for `site` and verify the bearer token.

	Looks up by `site` (the WAF autoname is `format:WAF-{site}`) so the
	check is a single indexed lookup, not a scan over Password records.
	"""
	try:
		waf_name = frappe.db.get_value("WAF", {"site": site}, "name")
	except Exception:
		return False
	if not waf_name:
		return False
	stored = (
		get_decrypted_password("WAF", waf_name, "waf_log_token")
		if frappe.db.get_value("WAF", waf_name, "waf_log_token")
		else None
	)
	if not stored:
		return False
	return _consttime_eq(stored, token)


def _consttime_eq(a: str, b: str) -> bool:
	"""Constant-time compare so timing side-channels can't leak the token."""
	if len(a) != len(b):
		return False
	out = 0
	for x, y in zip(a, b, strict=False):
		out |= ord(x) ^ ord(y)
	return out == 0


def _site_server(site: str) -> str | None:
	return frappe.db.get_value("Site", site, "server")


def _coerce_timestamp(value: str | None):
	"""ModSecurity serial timestamps are like ``06/Jul/2026:12:00:00 +0000``.

	Frappe can parse most natural-language dates; if it can't, fall back to
	None so the row is still persisted (transaction_id is the unique key).
	"""
	from frappe.utils import get_datetime

	if not value:
		return None
	try:
		return get_datetime(value)
	except Exception:
		return None


_SEVERITY_SET = {"CRITICAL", "ERROR", "WARNING", "NOTICE", "INFO", "DEBUG"}
_ACTION_SET = {"Intercepted", "Passed"}


def _coerce_severity(value: str | None) -> str | None:
	if not value:
		return None
	v = value.upper().strip()
	return v if v in _SEVERITY_SET else None


def _coerce_action(value: str | None) -> str | None:
	if not value:
		return None
	v = value.strip()
	return v if v in _ACTION_SET else None


def _coerce_truncated(value: str | None, limit: int) -> str | None:
	if value is None:
		return None
	if len(value) <= limit:
		return value
	return value[: limit - 3] + "..."


# ----------------------------------------------------------------------
# Dashboard listing (auth'd desk users)
# ----------------------------------------------------------------------


@frappe.whitelist()
def get_logs(site: str | None = None, start: int = 0, limit: int = 50) -> dict:
	"""Read-only listing for the WAF dashboard view.

	Each row is trimmed (raw_log truncated in the listing payload) to keep
	the desk responsive — the full row is retrievable via standard DocType
	get on the returned name.
	"""
	filters: dict[str, Any] = {}
	if site:
		filters["site"] = site
	rows = frappe.get_all(
		"WAF Log",
		filters=filters,
		fields=[
			"name",
			"transaction_id",
			"timestamp",
			"site",
			"server",
			"client_ip",
			"request_method",
			"request_uri",
			"rule_id",
			"rule_msg",
			"severity",
			"action",
		],
		order_by="timestamp desc",
		start=start,
		page_length=limit,
	)
	total = frappe.db.count("WAF Log", filters=filters)
	return {"rows": rows, "total": total}
