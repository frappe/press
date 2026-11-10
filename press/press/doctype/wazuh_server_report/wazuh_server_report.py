# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from press.press.doctype.server.server import UNREGISTERED_WAZUH_AGENT_STATUS, WAZUH_SERVER_TYPES
from press.press.doctype.wazuh_vulnerability.wazuh_vulnerability import sync_vulnerabilities
from press.utils import log_error
from press.wazuh import WazuhIndexer, WazuhManager, wazuh_datetime


class WazuhServerReport(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.wazuh_sca_policy_result.wazuh_sca_policy_result import WazuhSCAPolicyResult

		agent_id: DF.Data | None
		agent_status: DF.Data | None
		agent_version: DF.Data | None
		last_keep_alive: DF.Datetime | None
		operating_system: DF.Data | None
		sca_policies: DF.Table[WazuhSCAPolicyResult]
		server: DF.DynamicLink
		server_type: DF.Literal[
			"Server",
			"Database Server",
			"Proxy Server",
			"Monitor Server",
			"Log Server",
			"Registry Server",
			"Analytics Server",
			"Trace Server",
			"NAT Server",
			"NFS Server",
		]
		synced_at: DF.Datetime | None
		vulnerabilities_critical: DF.Int
		vulnerabilities_high: DF.Int
		vulnerabilities_low: DF.Int
		vulnerabilities_medium: DF.Int
	# end: auto-generated types

	def record_unregistered_agent(self):
		"""The manager has no record of the agent, so nothing it reported before is current."""
		self.agent_id = None
		self.agent_status = UNREGISTERED_WAZUH_AGENT_STATUS
		self.last_keep_alive = None
		self.record_sca_results([])
		self.record_severity_counts({})
		self.synced_at = now_datetime()

	def record_agent(self, agent: dict):
		self.agent_id = agent["id"]
		self.agent_status = agent.get("status")
		self.agent_version = agent.get("version")
		self.operating_system = agent.get("os", {}).get("name")
		self.last_keep_alive = wazuh_datetime(agent.get("lastKeepAlive"))
		self.synced_at = now_datetime()

	def record_sca_results(self, results: list[dict]):
		self.sca_policies = []
		for result in results:
			self.append(
				"sca_policies",
				{
					"policy_id": result.get("policy_id"),
					"policy_name": result.get("name"),
					"passed": result.get("pass"),
					"failed": result.get("fail"),
					"invalid": result.get("invalid"),
					"total_checks": result.get("total_checks"),
					"score": result.get("score"),
					"scan_end": wazuh_datetime(result.get("end_scan")),
				},
			)

	def record_severity_counts(self, counts: dict[str, int]):
		self.vulnerabilities_critical = counts.get("Critical", 0)
		self.vulnerabilities_high = counts.get("High", 0)
		self.vulnerabilities_medium = counts.get("Medium", 0)
		self.vulnerabilities_low = counts.get("Low", 0)


def sync_wazuh_reports():
	"""Refresh the report of every server with an agent, and its Critical and High vulnerabilities."""
	if not frappe.db.get_single_value("Press Settings", "wazuh_api_url"):
		return
	manager, indexer = WazuhManager(), WazuhIndexer()
	manager.authenticate()
	for server_type, server in servers_with_wazuh_agent():
		frappe.db.savepoint("wazuh_report")
		try:
			sync_report(manager, indexer, server_type, server)
		except Exception:
			# One unreachable agent must not stop the sweep over the rest of the fleet
			frappe.db.rollback(save_point="wazuh_report")
			log_error("Wazuh Report Sync Exception", server_type=server_type, server=server)


def servers_with_wazuh_agent():
	filters = {"is_wazuh_agent_installed": 1, "status": ("!=", "Archived")}
	for server_type in WAZUH_SERVER_TYPES:
		for server in frappe.get_all(server_type, filters=filters, pluck="name"):
			yield server_type, server


def sync_report(manager: WazuhManager, indexer: WazuhIndexer, server_type: str, server: str):
	report = get_report(server_type, server)
	agent = manager.get_agent(server)
	if not agent:
		report.record_unregistered_agent()
		report.save()
		sync_vulnerabilities(server_type, server, "", [])
		return
	report.record_agent(agent)
	report.record_sca_results(manager.sca_results(agent["id"]))
	report.record_severity_counts(indexer.severity_counts(server))
	report.save()
	sync_vulnerabilities(server_type, server, agent["id"], indexer.vulnerabilities(server))


def get_report(server_type: str, server: str) -> WazuhServerReport:
	name = frappe.db.exists("Wazuh Server Report", {"server_type": server_type, "server": server})
	if name:
		return WazuhServerReport("Wazuh Server Report", name)
	return WazuhServerReport({"doctype": "Wazuh Server Report", "server_type": server_type, "server": server})
