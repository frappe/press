# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.api.client import dashboard_whitelist
from press.press.doctype.site.site import Site
from press.saas.doctype.product_trial.product_trial import ProductTrial


class ProductTrialRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_request: DF.Link | None
		agent_job: DF.Link | None
		product_trial: DF.Link | None
		site: DF.Link | None
		status: DF.Literal["Pending", "Wait for Site", "Site Created", "Error", "Expired"]
		team: DF.Link | None
	# end: auto-generated types

	dashboard_fields = ["site", "status", "product_trial"]

	agent_job_step_to_frontend_step = {
		"New Site": {
			"New Site": "Building Site",
			"Install Apps": "Installing Apps",
			"Update Site Configuration": "Updating Configuration",
			"Enable Scheduler": "Finalizing Site",
			"Bench Setup Nginx": "Finalizing Site",
			"Reload Nginx": "Just a moment",
		},
		"Rename Site": {
			"Enable Maintenance Mode": "Starting",
			"Wait for Enqueued Jobs": "Starting",
			"Update Site Configuration": "Preparing Site",
			"Rename Site": "Preparing Site",
			"Bench Setup NGINX": "Preparing Site",
			"Reload NGINX": "Finalizing Site",
			"Disable Maintenance Mode": "Finalizing Site",
			"Enable Scheduler": "Just a moment",
		}
	}

	@dashboard_whitelist()
	def create_site(self, cluster=None):
		product: ProductTrial = frappe.get_doc("Product Trial", self.product_trial)
		site, agent_job_name = product.setup_trial_site(self.team, product.trial_plan, cluster)
		self.agent_job = agent_job_name
		self.site = site.name
		self.status = "Wait for Site"
		self.save(ignore_permissions=True)

	def get_user_details(self):
		user = frappe.db.get_value("Team", self.team, "user")
		return frappe.db.get_value(
			"User", user, ["email", "first_name", "last_name"], as_dict=True
		)

	@dashboard_whitelist()
	def get_login_sid(self):
		email = frappe.db.get_value("Team", self.team, "user")
		return frappe.get_doc("Site", self.site).get_login_sid(user=email)

	@dashboard_whitelist()
	def get_progress(self, current_progress=None):
		current_progress = current_progress or 0
		if self.agent_job:
			filters = {"name": self.agent_job, "site": self.site}
		else:
			filters = {"site": self.site, "job_type": ["in", ["New Site", "Rename Site"]]}
		job_name, status, job_type = frappe.db.get_value(
			"Agent Job",
			filters,
			["name", "status", "job_type"],
		)
		if status == "Success":
			frappe.db.set_value("Product Trial Request", self.name, "status", "Site Created")
			return {"progress": 100}
		elif status == "Running":
			steps = frappe.db.get_all(
				"Agent Job Step",
				filters={"agent_job": job_name},
				fields=["step_name", "status"],
				order_by="creation asc",
			)
			done = [s for s in steps if s.status in ("Success", "Skipped", "Failure")]
			progress = len(done) / len(steps) * 100
			if progress <= current_progress:
				progress = current_progress
			current_running_step = ""
			for step in steps:
				if step.status == "Running":
					current_running_step = self.agent_job_step_to_frontend_step.get(job_type, {}).get(step.step_name, step.step_name)
					break
			return {"progress": progress, "current_step": current_running_step}
		elif status == "Failure" or status == "Delivery Failure":
			frappe.db.set_value("Product Trial Request", self.name, "status", "Error")
			return {"progress": current_progress, "error": True}
		else:
			# If agent job is undelivered, pending
			return {"progress": current_progress}
