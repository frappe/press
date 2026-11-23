# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import TYPE_CHECKING, cast
from urllib.parse import urlsplit

import frappe
import requests
from frappe.utils import convert_utc_to_system_timezone, get_datetime

if TYPE_CHECKING:
	from press.press.doctype.press_settings.press_settings import PressSettings

VULNERABILITY_INDEX = "wazuh-states-vulnerabilities-*"
SYNCED_VULNERABILITY_SEVERITIES = ("Critical", "High")
VULNERABILITY_FIELDS = [
	"vulnerability.id",
	"vulnerability.severity",
	"vulnerability.score.base",
	"vulnerability.detected_at",
	"vulnerability.published_at",
	"vulnerability.description",
	"vulnerability.reference",
	"package.name",
	"package.version",
]
VULNERABILITY_PAGE_SIZE = 1000
MAX_VULNERABILITIES_PER_AGENT = 10_000  # index.max_result_window, past which from/size paging errors
INDEXER_PORT = 9200


class WazuhManager:
	"""Client for the Wazuh manager REST API.

	The single interface for Press to talk to the Wazuh manager, mirroring
	`press.agent.Agent` (which talks to the per-server agent). Credentials live
	in Press Settings.
	"""

	def __init__(self):
		settings = press_settings()
		self.url = (settings.wazuh_api_url or "").rstrip("/")
		self.username = str(settings.wazuh_api_username or "")
		self.password = str(settings.get_password("wazuh_api_password", raise_exception=False) or "")
		self.verify = bool(settings.wazuh_api_verify_tls)
		if not (self.url and self.username and self.password):
			frappe.throw("Please configure the Wazuh API in Press Settings")
		self._token = None

	@property
	def token(self):
		if not self._token:
			response = requests.post(
				f"{self.url}/security/user/authenticate",
				auth=(self.username, self.password),
				verify=self.verify,
				timeout=(10, 30),
			)
			response.raise_for_status()
			self._token = response.json()["data"]["token"]
		return self._token

	def authenticate(self):
		"""Fetch a token now, so an unreachable manager fails once instead of once per server."""
		self._token = None
		return self.token

	def request(self, method, path, params=None):
		response = self._request(method, path, params)
		if response.status_code == 401:  # the token expires after 15 minutes, a fleet sweep outlives it
			self._token = None
			response = self._request(method, path, params)
		response.raise_for_status()
		return response.json()["data"]

	def _request(self, method, path, params):
		return requests.request(
			method,
			f"{self.url}{path}",
			headers={"Authorization": f"Bearer {self.token}"},
			params=params,
			verify=self.verify,
			timeout=(10, 30),
		)

	def get_agent(self, name):
		# Wazuh's `q` filter is a query language (`;`, `=`, `!=`, `>` are operators),
		# and the name comes from a Server docname. Match the returned name exactly so a
		# crafted name that broadens the filter can never resolve to a different agent.
		items = self.request("GET", "/agents", {"q": f"name={name}"}).get("affected_items", [])
		return next((item for item in items if item.get("name") == name), None)

	def delete_agent(self, name):
		agent = self.get_agent(name)
		if not agent:
			return
		self.request(
			"DELETE",
			"/agents",
			{"agents_list": agent["id"], "status": "all", "older_than": "0s", "purge": "true"},
		)

	def agent_statuses(self):
		"""Map of agent name -> status (active/disconnected/never_connected/pending)."""
		statuses = {}
		offset, limit = 0, 500
		while True:
			data = self.request("GET", "/agents", {"select": "name,status", "limit": limit, "offset": offset})
			for item in data.get("affected_items", []):
				statuses[item["name"]] = item.get("status")
			offset += limit
			if offset >= data.get("total_affected_items", 0):
				break
		return statuses

	def sca_results(self, agent_id):
		"""One row per SCA policy of the agent: pass, fail and score of its last scan."""
		return self.request("GET", f"/sca/{agent_id}", {"limit": 100}).get("affected_items", [])


class WazuhIndexer:
	"""Client for the Wazuh indexer.

	Wazuh 4.8 moved vulnerability detection out of the manager API, so the open
	vulnerabilities of an agent are only readable from the indexer. The client
	uses the configured API host for the indexer connection.
	"""

	def __init__(self):
		settings = press_settings()
		self.url = indexer_url(settings.wazuh_api_url)
		self.username = str(settings.wazuh_indexer_username or "")
		self.password = str(settings.get_password("wazuh_indexer_password", raise_exception=False) or "")
		self.verify = bool(settings.wazuh_api_verify_tls)
		if not (self.url and self.username and self.password):
			frappe.throw("Please configure the Wazuh API and the indexer user in Press Settings")

	def search(self, body):
		response = requests.post(
			f"{self.url}/{VULNERABILITY_INDEX}/_search",
			json=body,
			auth=(self.username, self.password),
			verify=self.verify,
			timeout=(10, 60),
		)
		response.raise_for_status()
		return response.json()

	def severity_counts(self, agent_name):
		"""Map of severity -> number of open vulnerabilities on the agent."""
		body = {
			"size": 0,
			"query": agent_filter(agent_name),
			"aggs": {"severity": {"terms": {"field": "vulnerability.severity", "size": 10}}},
		}
		buckets = self.search(body)["aggregations"]["severity"]["buckets"]
		return {bucket["key"]: bucket["doc_count"] for bucket in buckets}

	def vulnerabilities(self, agent_name, severities=SYNCED_VULNERABILITY_SEVERITIES):
		"""Open vulnerabilities of the agent with one of `severities`."""
		findings, offset = [], 0
		while True:
			hits = self.search(self.vulnerabilities_page(agent_name, severities, offset))["hits"]["hits"]
			findings.extend(hit["_source"] for hit in hits)
			offset += VULNERABILITY_PAGE_SIZE
			if len(hits) < VULNERABILITY_PAGE_SIZE:
				return findings
			if offset >= MAX_VULNERABILITIES_PER_AGENT:
				frappe.throw(
					f"{agent_name} has over {MAX_VULNERABILITIES_PER_AGENT} findings; narrow the severities"
				)

	def vulnerabilities_page(self, agent_name, severities, offset):
		return {
			"from": offset,
			"size": VULNERABILITY_PAGE_SIZE,
			"sort": [{"_doc": "asc"}],
			"_source": VULNERABILITY_FIELDS,
			"query": agent_filter(agent_name, {"terms": {"vulnerability.severity": list(severities)}}),
		}


def press_settings() -> PressSettings:
	return cast("PressSettings", frappe.get_cached_doc("Press Settings"))


def indexer_url(api_url) -> str:
	parts = urlsplit(api_url or "")
	if not parts.hostname:
		return ""
	return f"{parts.scheme}://{parts.hostname}:{INDEXER_PORT}"


def agent_filter(agent_name, *extra_filters):
	return {"bool": {"filter": [{"term": {"agent.name": agent_name}}, *extra_filters]}}


def wazuh_datetime(value):
	"""A Wazuh ISO timestamp, which is UTC, as a naive datetime in the system timezone."""
	parsed = get_datetime(value) if value else None
	if not parsed or parsed.year == 9999:  # 9999 is Wazuh's placeholder for an agent that never connected
		return None
	return convert_utc_to_system_timezone(parsed.replace(tzinfo=None)).replace(tzinfo=None)
