# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from typing import Any

import frappe
import requests
from frappe.utils.password import get_decrypted_password

from press.mcp.guardrails.redaction import redact
from press.mcp.tools.telemetry.config import DEFAULT_TIMEOUT


def prometheus_get(endpoint: str, params: dict[str, Any]) -> dict:
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		frappe.throw("Monitor server not configured in Press Settings")

	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")
	url = f"https://{monitor_server}/prometheus/api/v1/{endpoint}"

	try:
		response = requests.get(url, params=params, auth=("frappe", str(password)), timeout=DEFAULT_TIMEOUT)
		response.raise_for_status()
	except requests.Timeout:
		frappe.throw("Prometheus query timed out. Try a shorter range, larger step, or smaller limit.")
	except requests.HTTPError:
		frappe.throw(f"Prometheus request failed with HTTP {response.status_code}")
	except requests.RequestException as e:
		frappe.throw(f"Prometheus request failed: {e}")

	data = response.json()
	if data.get("status") != "success":
		frappe.throw(data.get("error") or "Prometheus query failed")

	return redact(data)


def elasticsearch_post(body: dict, *, should_redact: bool = True) -> dict:
	log_server = frappe.db.get_single_value("Press Settings", "log_server")
	if not log_server:
		frappe.throw("Log server not configured in Press Settings")

	password = get_decrypted_password("Log Server", log_server, "kibana_password")
	url = f"https://{log_server}/elasticsearch/filebeat-*/_search"

	try:
		response = requests.post(url, json=body, auth=("frappe", str(password)), timeout=DEFAULT_TIMEOUT)
		response.raise_for_status()
	except requests.Timeout:
		frappe.throw("Elasticsearch query timed out. Try a shorter time window or smaller limit.")
	except requests.HTTPError:
		frappe.throw(f"Elasticsearch request failed with HTTP {response.status_code}")
	except requests.RequestException as e:
		frappe.throw(f"Elasticsearch request failed: {e}")

	data = response.json()
	return redact(data) if should_redact else data
