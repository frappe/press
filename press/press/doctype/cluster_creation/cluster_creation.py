# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import typing

import frappe
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime

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

	@property
	def source_cluster_doc(self) -> "Cluster":
		return frappe.get_doc("Cluster", self.source_cluster)

	@flow
	def execute(self):
		self.create_cluster_record()
		self.copy_images_if_needed()
		self.create_proxy_server()
		self.create_server_pairs()

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
		proxy, _ = cluster.create_server("Proxy Server", _DEFAULT_SERVER_TITLE)
		self.kv.set("proxy_server", proxy.name)

	@task
	def create_server_pairs(self):
		"""Create DB and App Server Pairs"""
		cluster: Cluster = frappe.get_doc("Cluster", self.new_cluster)
		cluster.proxy_server = self.kv.get("proxy_server")

		num_pairs = cluster.auto_cluster_app_server_count or 1
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

		for pair_index in range(1, num_pairs + 1):
			db_server, _ = cluster.create_server(
				"Database Server",
				f"Public DB Server {pair_index}",
				plan=db_plan,
			)
			cluster.database_server = db_server.name
			cluster.create_server(
				"Server",
				f"Public App Server {pair_index}",
				plan=app_plan,
				public=True,
			)
			frappe.db.commit()
