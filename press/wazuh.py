# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
import requests


class WazuhManager:
	"""Client for the Wazuh manager REST API.

	The single interface for Press to talk to the Wazuh manager, mirroring
	`press.agent.Agent` (which talks to the per-server agent). Credentials live
	in Press Settings.
	"""

	def __init__(self):
		settings = frappe.get_cached_doc("Press Settings")
		self.url = (settings.wazuh_api_url or "").rstrip("/")
		self.username = settings.wazuh_api_username
		self.password = settings.get_password("wazuh_api_password", raise_exception=False)
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

	def request(self, method, path, params=None):
		response = requests.request(
			method,
			f"{self.url}{path}",
			headers={"Authorization": f"Bearer {self.token}"},
			params=params,
			verify=self.verify,
			timeout=(10, 30),
		)
		response.raise_for_status()
		return response.json()["data"]

	def get_agent(self, name):
		items = self.request("GET", "/agents", {"q": f"name={name}"}).get("affected_items", [])
		return items[0] if items else None

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
