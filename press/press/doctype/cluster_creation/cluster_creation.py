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
		self._create_cluster_creation_incident(workflow)

	@property
	def source_cluster_doc(self) -> "Cluster":
		return frappe.get_doc("Cluster", self.source_cluster)

	@flow
	def execute(self):
		self.create_cluster_record()
		self.copy_images_if_needed()
		self.create_proxy_server()
		self.wait_for_proxy_server()

		for i in range(1, (self.source_cluster_doc.auto_cluster_app_server_count or 1) + 1):
			self.create_server_pairs(i)
			self.wait_for_server_pairs(i)

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
			"public": source.public,
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
		_, app_job = cluster.create_server(
			"Server",
			f"Public App Server {pair_index}",
			plan=app_plan,
			public=True,
		)
		self.kv.set(f"db_job_name_{pair_index}", db_job.name)
		self.kv.set(f"app_job_name_{pair_index}", app_job.name)

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
