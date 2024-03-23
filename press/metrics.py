# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from prometheus_client import (
	CollectorRegistry,
	Gauge,
	generate_latest,
)
from werkzeug.wrappers import Response
import frappe
from frappe.utils import cint


class MetricsRenderer:
	def __init__(self, path, status_code=None):
		self.path = path
		self.registry = CollectorRegistry(auto_describe=True)

	def get_status(self, metric, doctype, status_field="status", filters=None):
		if filters is None:
			filters = {}
		c = Gauge(metric, "", [status_field], registry=self.registry)
		rows = frappe.get_all(
			doctype,
			fields=[status_field, "count(*) as count"],
			filters=filters,
			group_by=status_field,
			order_by=f"{status_field} asc",
			ignore_ifnull=True,
		)
		for row in rows:
			c.labels(row[status_field]).set(row.count)

	def metrics(self):
		suspended_builds = Gauge(
			"press_builds_suspended", "Are docker builds suspended", registry=self.registry
		)
		suspended_builds.set(
			cint(frappe.db.get_value("Press Settings", None, "suspend_builds"))
		)
		self.get_status(
			"press_deploy_candidate_total",
			"Deploy Candidate",
			filters={"status": ("!=", "Success")},
		)

		self.get_status(
			"press_site_total", "Site", filters={"status": ("not in", ("Archived", "Active"))}
		)
		self.get_status("press_bench_total", "Bench", filters={"status": ("!=", "Archived")})
		self.get_status("press_server_total", "Server")

		self.get_status("press_database_server_total", "Database Server")
		self.get_status("press_virtual_machine_total", "Virtual Machine")

		self.get_status(
			"press_site_backup_total", "Site Backup", filters={"status": ("!=", "Success")}
		)
		self.get_status(
			"press_site_update_total", "Site Update", filters={"status": ("!=", "Success")}
		)
		self.get_status("press_site_migration_total", "Site Migration")
		self.get_status("press_site_upgrade_total", "Version Upgrade")

		self.get_status("press_press_job_total", "Press Job")
		self.get_status(
			"press_ansible_play_total", "Ansible Play", filters={"status": ("!=", "Success")}
		)
		self.get_status(
			"press_agent_job_total", "Agent Job", filters={"status": ("!=", "Success")}
		)

		self.get_status("press_error_log_total", "Error Log", "method")

		return generate_latest(self.registry).decode("utf-8")

	def can_render(self):
		if self.path in ("metrics",):
			return True

	def render(self):
		response = Response()
		response.mimetype = "text"
		response.data = self.metrics()
		return response
