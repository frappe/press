# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.database_server.database_server import DatabaseServer
from press.press.doctype.server.server import Server
from press.press.doctype.server_plan.server_plan import ServerPlan


class IncidentPattern(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.incident_management.doctype.incident_pattern_investigation.incident_pattern_investigation import (
			IncidentPatternInvestigation,
		)

		causes: DF.Data
		investigations: DF.Table[IncidentPatternInvestigation]
		server: DF.DynamicLink | None
		server_type: DF.Link | None
	# end: auto-generated types

	def _get_requirements_from_pattern(self) -> tuple[bool, bool]:
		"""We have a cause list already stored in the patterns"""
		cause_list = self.causes.split(",")
		requires_cpu = any(
			cause == "has_high_cpu_load" or cause == "has_high_system_load" for cause in cause_list
		)
		requires_memory = any(cause == "has_high_memory_usage" for cause in cause_list)
		return requires_cpu, requires_memory

	def _get_plan_recommendation(self, server: Server | DatabaseServer) -> ServerPlan | None:
		"""Auto upgrade public server to the next available plan depending on the pattern recognized"""
		requires_cpu, requires_memory = self._get_requirements_from_pattern()
		try:
			return server.get_next_plan(requires_cpu=requires_cpu, requires_memory=requires_memory)
		except frappe.ValidationError:
			# No higher plan present!
			return None

	def _get_upgrade_target_name(self) -> str:
		is_unified_server = frappe.db.get_value(self.server_type, self.server, "is_unified_server")
		return (
			f"{self.server} ({'Application Server' if self.server_type == 'Server' else 'Database Server'})"
			if not is_unified_server
			else f"{self.server} (Unified Server)"
		)

	def _notify_plan_recommendation(self, server_doc: Server | DatabaseServer, recommended_plan: ServerPlan):
		"""Send an email notification for the recommended plan upgrade."""
		frappe.sendmail(
			subject=f"Plan Upgrade Recommended for Server: {server_doc.title or server_doc.name}",
			recipients=get_communication_info(
				"Email", "Server Activity", server_doc.doctype, server_doc.name
			),
			template="plan_upgrade_recommendation",
			args={
				"instance_type": recommended_plan.instance_type,
				"vcpu": recommended_plan.vcpu,
				"memory": recommended_plan.memory // 1024,
				"server_name": server_doc.name,
				"upgrade_target": self._get_upgrade_target_name(),
			},
			now=True,
		)

	def after_insert(self):
		"""After a pattern is recognized, suggest or automatically upgrade server plans based on the pattern."""
		server_doc: Server | DatabaseServer = frappe.get_doc(self.server_type, self.server)
		recommended_plan = self._get_plan_recommendation(server_doc)

		if not recommended_plan:
			return

		if server_doc.public:
			# Automatically upgrade public servers to the recommended plan
			server_doc.change_plan(recommended_plan.name)
		else:
			# Send notification emails in case of non-public servers
			self._notify_plan_recommendation(server_doc, recommended_plan)
