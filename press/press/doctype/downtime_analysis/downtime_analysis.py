# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import get_job_status
from frappe.utils.password import get_decrypted_password

from press.press.doctype.downtime_analysis.generate_metrics import (
	generate_server_downtime_report,
	generate_site_downtime_report,
	get_data_for_all_clusters,
	is_report_available,
)


class DowntimeAnalysis(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		end_date: DF.Date
		raw_data: DF.LongText | None
		rq_job_id: DF.Data | None
		start_date: DF.Date
		status: DF.Data | None
	# end: auto-generated types

	def load_from_db(self):
		frappe.only_for("Desk User")

	@frappe.whitelist()
	def fetch_report(self):
		frappe.only_for("Desk User")
		if not (self.start_date and self.end_date):
			frappe.throw("Start Date and End Date are required to fetch the report.")
		if self.start_date > self.end_date:
			frappe.throw("Start Date cannot be greater than End Date.")

		if is_report_available(str(self.start_date), str(self.end_date)):
			self.status = "Report Available"
			self.raw_data = json.dumps(
				self.generate_and_prepare_report(
					start_date=str(self.start_date), end_date=str(self.end_date), prepare=True
				)
			)
			return

		job_id = f"downtime_analysis||{self.start_date!s}||{self.end_date!s}"
		self.rq_job_id = job_id
		job_status = get_job_status(job_id)
		if job_status:
			self.status = f"Job {job_status}"
			frappe.msgprint("Refresh after some time to check the job status.")
			return

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			method="generate_and_prepare_report",
			queue="default",
			timeout=1200,
			job_id=job_id,
			deduplicate=True,
			start_date=str(self.start_date),
			end_date=str(self.end_date),
			prepare=True,
		)

		self.status = "Job Queued"
		frappe.msgprint("Refresh after some time to check the job status.")

	def generate_and_prepare_report(self, start_date: str, end_date: str, prepare=False):
		clusters = frappe.db.get_all(
			"Cluster",
			filters={
				"public": 1,
			},
			pluck="name",
		)

		monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
		data = get_data_for_all_clusters(
			start_date=start_date,
			end_date=end_date,
			clusters=clusters,
			prometheus_server=monitor_server,
			prometheus_auth=(
				"frappe",
				get_decrypted_password("Monitor Server", monitor_server, "grafana_password"),
			),
		)

		report_data = {}
		report_data["server"] = generate_server_downtime_report(
			start_date=start_date,
			end_date=end_date,
			server_downtime_data=data.get("server_downtime", {}),
			clusters=clusters,
		)
		report_data["site"] = generate_site_downtime_report(
			start_date=start_date,
			end_date=end_date,
			site_downtime_data=data.get("site_downtime", {}),
			clusters=clusters,
		)

		return report_data

	def db_insert(self, *args, **kwargs):
		raise NotImplementedError

	def db_update(self):
		raise NotImplementedError

	def delete(self):
		raise NotImplementedError

	@staticmethod
	def get_list(filters=None, page_length=20, **kwargs):
		pass

	@staticmethod
	def get_count(filters=None, **kwargs):
		pass

	@staticmethod
	def get_stats(**kwargs):
		pass
