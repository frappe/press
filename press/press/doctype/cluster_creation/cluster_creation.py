# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import typing

import frappe
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime

from press.utils import log_error
from press.workflow_engine.doctype.press_workflow.decorators import flow, task
from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder

if typing.TYPE_CHECKING:
	from frappe.types import DF

	from press.press.doctype.cluster.cluster import Cluster
	from press.workflow_engine.doctype.press_workflow.press_workflow import PressWorkflow

_DEFAULT_SERVER_TITLE = "First"


class ClusterCreation(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		duration: DF.Duration | None
		end: DF.Datetime | None
		new_cluster: DF.Link | None
		source_cluster: DF.Link
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]

	# end: auto-generated types

	def after_insert(self):
		self.db_set({"start": now_datetime(), "status": "Running"})
		self.execute.run_as_workflow()

	def on_workflow_success(self, workflow: "PressWorkflow"):
		self.db_set({"status": "Success", "end": now_datetime()})

	def on_workflow_failure(self, workflow: "PressWorkflow"):
		self.db_set({"status": "Failure", "end": now_datetime()})
		self._revert_source_cluster()
		self._create_cluster_creation_incident(workflow)

	def _revert_source_cluster(self):
		"""Re-expose the source cluster on workflow failure.

		The threshold trigger marked the source cluster non-public and set
		``auto_cluster_triggered`` so no new servers land on it while the
		successor is provisioned.  If provisioning fails the source would be
		stranded (non-public + triggered = never retried), so re-publish it and
		clear the flag to allow a retry on the next threshold hit.  The incident
		raised alongside this keeps a human in the loop.
		"""
		frappe.db.set_value(
			"Cluster",
			self.source_cluster,
			{"public": 1, "auto_cluster_triggered": 0},
		)

	@property
	def source_cluster_doc(self) -> "Cluster":
		return frappe.get_doc("Cluster", self.source_cluster)

	@flow
	def execute(self):
		self.create_cluster_record()
		self.copy_images_if_needed()
		self.clone_server_plans()
		self.reconfigure_monitor_server()
		self.create_proxy_server()
		self.wait_for_proxy_server()
		self.setup_proxy_ssh()
		self.setup_proxy_proxysql()

		for i in range(1, (self.source_cluster_doc.auto_cluster_app_server_count or 1) + 1):
			self.create_server_pairs(i)
			self.wait_for_server_pairs(i)

		self.add_servers_to_public_benches()
		self.enable_new_servers_for_placement()
		self.mark_new_cluster_public()

	@task
	def create_cluster_record(self):
		"""Create Cluster"""
		if self.new_cluster:
			return

		source: Cluster = self.source_cluster_doc
		root_name = source.derived_cluster_from or source.name
		new_name = make_autoname(f"{root_name}-.#")

		cluster_data: dict = {
			"doctype": "Cluster",
			"name": new_name,
			"title": source.title or root_name,
			"status": "Active",
			"cloud_provider": source.cloud_provider,
			"region": source.region,
			"availability_zone": source.availability_zone,
			"ssh_key": source.ssh_key,
			# Stay non-public throughout provisioning; mark_new_cluster_public
			# flips this on only once benches are deployed and ready.
			"public": 0,
			"hybrid": source.hybrid,
			"beta": source.beta,
			"team": source.team,
			"country": source.country,
			"default_app_server_plan": source.default_app_server_plan,
			"default_db_server_plan": source.default_db_server_plan,
			"default_app_server_plan_type": source.default_app_server_plan_type,
			"default_db_server_plan_type": source.default_db_server_plan_type,
			"by_default_select_unified_mode": source.by_default_select_unified_mode,
			"has_arm_support": source.has_arm_support,
			"has_unified_server_support": source.has_unified_server_support,
			"has_add_on_storage_support": source.has_add_on_storage_support,
			"enable_autoscaling": source.enable_autoscaling,
			"enable_periodic_flush_table": source.enable_periodic_flush_table,
			"flush_table_execution_hour": source.flush_table_execution_hour,
			"disable_public_ips_for_servers": source.disable_public_ips_for_servers,
			"enable_auto_cluster": source.enable_auto_cluster,
			"max_servers": source.max_servers,
			"derived_cluster_from": root_name,
			"auto_cluster_app_server_count": source.auto_cluster_app_server_count or 1,
		}

		if source.cloud_provider == "AWS EC2":
			cluster_data["aws_access_key_id"] = source.aws_access_key_id
			cluster_data["aws_secret_access_key"] = source.get_password("aws_secret_access_key")
		elif source.cloud_provider == "Hetzner":
			cluster_data["hetzner_api_token"] = source.get_password("hetzner_api_token")
		elif source.cloud_provider == "OCI":
			cluster_data["oci_user"] = source.oci_user
			cluster_data["oci_tenancy"] = source.oci_tenancy
			cluster_data["oci_public_key"] = source.oci_public_key
			cluster_data["oci_private_key"] = source.get_password("oci_private_key")
		elif source.cloud_provider == "DigitalOcean":
			cluster_data["digital_ocean_api_token"] = source.get_password("digital_ocean_api_token")
		elif source.cloud_provider == "Frappe Compute":
			cluster_data["frappe_compute_base_url"] = source.frappe_compute_base_url
			cluster_data["frappe_compute_api_key"] = source.frappe_compute_api_key
			cluster_data["frappe_compute_api_secret"] = source.get_password("frappe_compute_api_secret")

		new_cluster = frappe.get_doc(cluster_data).insert(ignore_permissions=True)
		self.db_set("new_cluster", new_cluster.name)

	@task(queue="long", timeout=3600)
	def copy_images_if_needed(self):
		"""Copy VM Images"""
		cluster: Cluster = frappe.get_doc("Cluster", self.new_cluster)
		if cluster.images_available >= 1:
			return
		cluster._add_images()

	@task
	def create_proxy_server(self):
		"""Create Proxy Server"""
		cluster: Cluster = frappe.get_doc("Cluster", self.new_cluster)
		proxy, proxy_job = cluster.create_server("Proxy Server", _DEFAULT_SERVER_TITLE)
		self.kv.set("proxy_server", proxy.name)
		self.kv.set("proxy_job_name", proxy_job.name)

	@task
	def create_server_pairs(self, pair_index=1):
		"""Create DB and App Server Pairs"""
		cluster: Cluster = frappe.get_doc("Cluster", self.new_cluster)
		cluster.proxy_server = self.kv.get("proxy_server")

		app_plan = (
			frappe.get_doc("Server Plan", cluster.default_app_server_plan)
			if cluster.default_app_server_plan
			else None
		)
		db_plan = (
			frappe.get_doc("Server Plan", cluster.default_db_server_plan)
			if cluster.default_db_server_plan
			else None
		)

		db_server, db_job = cluster.create_server(
			"Database Server",
			f"Public DB Server {pair_index}",
			plan=db_plan,
		)
		cluster.database_server = db_server.name
		app_server, app_job = cluster.create_server(
			"Server",
			f"Public App Server {pair_index}",
			plan=app_plan,
			public=True,
		)
		self.kv.set(f"db_job_name_{pair_index}", db_job.name)
		self.kv.set(f"app_job_name_{pair_index}", app_job.name)
		self.kv.set(f"app_server_{pair_index}", app_server.name)

	@task
	def wait_for_proxy_server(self):
		"""Wait for Proxy Server Job"""
		job_name = self.kv.get("proxy_job_name")
		status = frappe.db.get_value("Press Job", job_name, "status")
		if status in ("Pending", "Running"):
			self.defer_current_task(f"Proxy server job {job_name} still {status}")
		if status == "Failure":
			raise RuntimeError(f"Proxy server creation job {job_name} failed")

	@task
	def wait_for_server_pairs(self, pair_index=1):
		"""Wait for DB and App Server Pair Jobs"""
		db_job_name = self.kv.get(f"db_job_name_{pair_index}")
		app_job_name = self.kv.get(f"app_job_name_{pair_index}")
		db_status = frappe.db.get_value("Press Job", db_job_name, "status")
		app_status = frappe.db.get_value("Press Job", app_job_name, "status")
		if db_status in ("Pending", "Running") or app_status in ("Pending", "Running"):
			self.defer_current_task(
				f"Server pair {pair_index} jobs still running (db={db_status}, app={app_status})"
			)
		failures = []
		if db_status == "Failure":
			failures.append(f"DB server job {db_job_name}")
		if app_status == "Failure":
			failures.append(f"App server job {app_job_name}")
		if failures:
			raise RuntimeError(f"Server pair {pair_index} creation failed: {', '.join(failures)}")

	@task
	def clone_server_plans(self):
		"""Clone Server Plans to New Cluster"""
		for plan_name in frappe.get_all("Server Plan", {"cluster": self.source_cluster}, pluck="name"):
			new_name = f"{plan_name} - {self.new_cluster}"
			if frappe.db.exists("Server Plan", new_name):
				continue
			plan = frappe.copy_doc(frappe.get_doc("Server Plan", plan_name))
			plan.name = None
			plan.cluster = self.new_cluster
			plan.insert(set_name=new_name, ignore_permissions=True, ignore_if_duplicate=True)

	@task(queue="long", timeout=1800)
	def reconfigure_monitor_server(self):
		"""Reconfigure Monitor Server"""
		# Best effort: monitoring is observability, not on the critical path.
		# _reconfigure_monitor_server swallows its own Ansible errors.
		monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
		if not monitor_server:
			return
		frappe.get_doc("Monitor Server", monitor_server)._reconfigure_monitor_server()

	@task(queue="long", timeout=1800)
	def setup_proxy_ssh(self):
		"""Setup SSH Proxy"""
		# Non-fatal: SSH proxy is convenience tooling, not required for the
		# cluster to serve traffic. On failure mark the proxy Broken and move on
		# rather than failing the whole cluster creation.
		proxy = frappe.get_doc("Proxy Server", self.kv.get("proxy_server"))
		if proxy.is_ssh_proxy_setup:
			return

		if not proxy.ssh_certificate_authority:
			ca = frappe.db.get_single_value("Press Settings", "ssh_certificate_authority")
			if not ca:
				log_error("SSH Proxy setup skipped: no SSH Certificate Authority", proxy=proxy.name)
				proxy.db_set("status", "Broken")
				return
			proxy.db_set("ssh_certificate_authority", ca)
			proxy.reload()

		proxy._setup_ssh_proxy()
		proxy.reload()
		if not proxy.is_ssh_proxy_setup:
			log_error("SSH Proxy setup failed", proxy=proxy.name)
			proxy.db_set("status", "Broken")

	@task(queue="long", timeout=1800)
	def setup_proxy_proxysql(self):
		"""Setup ProxySQL"""
		# Non-fatal, same as setup_proxy_ssh: flag the proxy Broken and continue
		# instead of failing the whole cluster creation.
		proxy = frappe.get_doc("Proxy Server", self.kv.get("proxy_server"))
		if proxy.is_proxysql_setup:
			return
		proxy._setup_proxysql()
		proxy.reload()
		if not proxy.is_proxysql_setup:
			log_error("ProxySQL setup failed", proxy=proxy.name)
			proxy.db_set("status", "Broken")

	def _new_app_servers(self) -> list[str]:
		count = self.source_cluster_doc.auto_cluster_app_server_count or 1
		return [self.kv.get(f"app_server_{i}") for i in range(1, count + 1)]

	def _public_release_groups(self) -> list[str]:
		return frappe.get_all(
			"Release Group",
			{"public": 1, "enabled": 1, "central_bench": 0},
			pluck="name",
		)

	@task(queue="long", timeout=3600)
	def add_servers_to_public_benches(self):
		"""Add App Servers to Public Benches"""
		app_servers = self._new_app_servers()
		for group_name in self._public_release_groups():
			rg = frappe.get_doc("Release Group", group_name)
			for server in app_servers:
				if any(s.server == server for s in rg.servers):
					continue
				rg.add_server(server, deploy=True)
				rg.reload()

	@task
	def enable_new_servers_for_placement(self):
		"""Enable New Servers for New Benches and Sites"""
		for server in self._new_app_servers():
			frappe.db.set_value("Server", server, {"use_for_new_benches": 1, "use_for_new_sites": 1})

	@task
	def mark_new_cluster_public(self):
		"""Mark New Cluster as Public"""
		frappe.db.set_value("Cluster", self.new_cluster, "public", 1)

	def _create_cluster_creation_incident(self, workflow: "PressWorkflow") -> None:
		cluster = self.new_cluster or self.source_cluster
		subject = f"Auto Cluster creation failed for {cluster}"

		open_incident = frappe.db.exists(
			"Incident",
			{
				"cluster": cluster,
				"subject": subject,
				"status": ["not in", ["Resolved", "Auto-Resolved", "Press-Resolved"]],
			},
		)
		if open_incident:
			return

		description = (
			f"Auto cluster creation failed for cluster {cluster}. "
			f"Source cluster: {self.source_cluster}. "
			f"Workflow: {workflow.name}. "
			"Review the workflow traceback and Press Job logs for details."
		)

		try:
			frappe.get_doc(
				{
					"doctype": "Incident",
					"cluster": cluster,
					"type": "Server Down",
					"subject": subject,
					"description": description,
				}
			).insert(ignore_permissions=True)
		except Exception:
			log_error(
				"Failed to create cluster creation incident",
				cluster=cluster,
				workflow=workflow.name,
			)
