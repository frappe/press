from __future__ import annotations

import time
from typing import TYPE_CHECKING

import frappe

from press.press.doctype.press_job.press_job import PressJob
from press.workflow_engine.doctype.press_workflow.decorators import flow, task

if TYPE_CHECKING:
	from press.press.doctype.on_prem_failover.on_prem_failover import OnPremFailover


class SetupOnPremFailoverJob(PressJob):
	@flow
	def execute(self):
		self.add_app_server_to_firewall()
		self.add_db_server_to_firewall()
		self.setup_wireguard_on_app_server()
		self.setup_wireguard_on_db_server()
		self.test_connectivity()
		self.setup_replication_for_app_server()
		self.setup_db_lsync_for_initial_sync()
		self.wait_for_initial_db_sync()
		self.rsync_new_db_files()
		self.setup_replica_in_on_prem_server()

	@property
	def failover_doc(self) -> OnPremFailover:
		if not hasattr(self, "_on_prem_failover_doc") or not self._on_prem_failover_doc:  # type: ignore
			self._on_prem_failover_doc = frappe.get_doc("On-Prem Failover", self.arguments_dict.failover)
		return self._on_prem_failover_doc  # type: ignore

	@task
	def add_app_server_to_firewall(self):
		"""Allow Wireguard Port Through Security Group on App Server"""
		self.failover_doc.add_app_server_to_firewall()

	@task
	def add_db_server_to_firewall(self):
		"""Allow Wireguard Port Through Security Group on DB Server"""
		self.failover_doc.add_db_server_to_firewall()

	@task
	def setup_wireguard_on_app_server(self):
		"""Setup Wireguard on App Server"""
		self.failover_doc.setup_wireguard_on_app_server()

	@task
	def setup_wireguard_on_db_server(self):
		"""Setup Wireguard on DB Server"""
		self.failover_doc.setup_wireguard_on_database_server()

	@task(queue="long", timeout=600)
	def test_connectivity(self):
		"""Test Connectivity to On-Prem Server"""
		self.failover_doc.check_connectivity_to_on_premise_server()
		self.failover_doc.reload()

		if (
			self.failover_doc.is_on_prem_server_ssh_from_app_server_working
			and self.failover_doc.is_on_prem_server_ssh_from_db_server_working
		):
			return

		self.defer_current_task()

	@task(queue="long", timeout=3600)
	def setup_replication_for_app_server(self):
		"""Setup Replication for App Server"""
		self.failover_doc._setup_app_server_replica()

	@task(queue="long", timeout=3600)
	def setup_db_lsync_for_initial_sync(self):
		"""Setup Lsyncd For Initial DB Sync"""
		self.failover_doc._setup_db_lsync_for_initial_sync()

	@task
	def wait_for_initial_db_sync(self):
		if (
			self.failover_doc.db_lsyncd_stop_at
			and frappe.utils.now_datetime() > self.failover_doc.db_lsyncd_stop_at
		):
			return
		time.sleep(1)
		self.defer_current_task()

	@task(queue="long", timeout=3600)
	def rsync_new_db_files(self):
		self.failover_doc._setup_db_rsync_for_final_sync()

	@task(queue="long", timeout=3600)
	def setup_replica_in_on_prem_server(self):
		self.failover_doc._setup_and_configure_database_replica()

	def on_press_job_success(self, _):
		self.failover_doc.is_db_server_failover_setup = True
		self.failover_doc.is_app_server_failover_setup = True
		self.failover_doc.save()
