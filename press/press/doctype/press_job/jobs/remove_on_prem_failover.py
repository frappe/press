from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

if TYPE_CHECKING:
	from press.press.doctype.on_prem_failover.on_prem_failover import OnPremFailover


class RemoveOnPremFailoverJob(PressJob):
	@flow
	def execute(self):
		self.remove_app_server_from_firewall()
		self.remove_db_server_from_firewall()
		self.stop_replication_from_app_server()
		self.stop_replication_from_db_server()
		self.delete_firewall()

	@property
	def failover_doc(self) -> OnPremFailover:
		if not hasattr(self, "_on_prem_failover_doc") or not self._on_prem_failover_doc:  # type: ignore
			self._on_prem_failover_doc = frappe.get_doc("On-Prem Failover", self.arguments_dict.failover)
		return self._on_prem_failover_doc  # type: ignore

	@task
	def remove_app_server_from_firewall(self):
		"""Remove Wireguard Port Access from App Server"""
		self.failover_doc.remove_app_server_from_firewall()

	@task
	def remove_db_server_from_firewall(self):
		"""Remove Wireguard Port Access from DB Server"""
		self.failover_doc.remove_db_server_from_firewall()

	@task(queue="long", timeout=1800)
	def stop_replication_from_app_server(self):
		"""Stop Replication from App Server"""
		self.failover_doc._stop_replication_from_app_server()

	@task(queue="long", timeout=1800)
	def stop_replication_from_db_server(self):
		"""Stop Replication from DB Server"""
		self.failover_doc._stop_replication_from_db_server()

	@task
	def delete_firewall(self):
		"""Delete Firewall"""
		self.failover_doc.delete_firewall()

	def on_press_job_success(self, _):
		self.failover_doc.is_db_server_failover_setup = False
		self.failover_doc.is_app_server_failover_setup = False
		self.failover_doc.enabled = False
		self.failover_doc.save()
