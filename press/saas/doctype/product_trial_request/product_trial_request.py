# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec

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
		signup_details: DF.JSON | None
		site: DF.Link | None
		status: DF.Literal["Pending", "Wait for Site", "Completing Setup Wizard", "Site Created", "Error", "Expired"]
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

	@frappe.whitelist()
	def get_setup_wizard_payload(self):
		data = frappe.get_value("Product Trial", self.product_trial, ["setup_wizard_completion_mode", "setup_wizard_payload_generator_script"], as_dict=True)
		if data.setup_wizard_completion_mode != "auto":
			frappe.throw("In manual Setup Wizard Completion Mode, the payload cannot be generated")
		if not data.setup_wizard_payload_generator_script:
			return {}
		signup_details = json.loads(self.signup_details)
		team_details = frappe.get_value("Team", self.team, ["name", "user", "country", "currency"], as_dict=True)
		team_user = frappe.get_doc("User", team_details.user)
		try:
			_locals = {
				"team": frappe._dict({
					"name": team_details.name,
					"user": frappe._dict({
						"email": team_user.email,
						"full_name": team_user.full_name or "",
						"first_name": team_user.first_name or "",
						"last_name": team_user.last_name or "",
					}),
					"country": team_details.country,
					"currency": team_details.currency
				}),
				"signup_details": frappe._dict(signup_details),
				"payload": frappe._dict()
			}
			safe_exec(
				data.setup_wizard_payload_generator_script,
				_locals=_locals,
				restrict_commit_rollback=True,
			)
			return frappe._dict(_locals.get("payload", {}))

		except Exception as e:
			frappe.log_error(title="Product Trial Reqeust Setup Wizard Payload Generation Error")
			frappe.throw(f"Failed to generate payload for Setup Wizard: {e}")

	@dashboard_whitelist()
	def create_site(self, cluster=None, signup_values=None):
		if not signup_values:
			signup_values = {}

		product: ProductTrial = frappe.get_doc("Product Trial", self.product_trial)
		# Validate signup values
		for field in product.signup_fields:
			if field.fieldname not in signup_values:
				if field.required:
					frappe.throw(f"Required field {field.label} is missing")
				else:
					signup_values[field.fieldname] = None
		self.signup_details = json.dumps(signup_values)
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
			mode = frappe.get_value("Product Trial", self.product_trial, "setup_wizard_completion_mode")
			if mode != "auto":
				frappe.db.set_value("Product Trial Request", self.name, "status", "Site Created")
				return {"progress": 100}
			else:
				if self.status == "Site Created":
					return {"progress": 100}
				elif self.status != "Completing Setup Wizard":
					self.status = "Completing Setup Wizard"
					self.complete_setup_wizard()
					self.save(ignore_permissions=True)
				return {"progress": 90, "current_step": "Completing Setup Wizard"}
		elif status == "Running":
			mode = frappe.get_value("Product Trial", self.product_trial, "setup_wizard_completion_mode")
			steps = frappe.db.get_all(
				"Agent Job Step",
				filters={"agent_job": job_name},
				fields=["step_name", "status"],
				order_by="creation asc",
			)
			done = [s for s in steps if s.status in ("Success", "Skipped", "Failure")]
			steps_count = len(steps)
			if mode == "auto":
				steps_count += 1
			progress = (len(done) / steps_count) * 100
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
		
	def complete_setup_wizard(self):
		frappe.enqueue_doc(
			"Product Trial Request",
			self.name,
			method="_complete_setup_wizard",
			timeout=600,
			enqueue_after_commit=True
		)
		
	def _complete_setup_wizard(self):
		if frappe.get_value("Product Trial Request", self.name, "status") != "Completing Setup Wizard":
			return
		data = self.get_setup_wizard_payload()
		try:
			site: "Site" = frappe.get_doc("Site", self.site)
			client = site.get_connection_as_admin()
			response = client.post_api("frappe.desk.page.setup_wizard.setup_wizard.setup_complete", {
				"args": json.dumps(data) 
			})
			if response["status"] == "ok":
				frappe.db.set_value("Product Trial Request", self.name, "status", "Site Created")
		except Exception as e:
			frappe.log_error(title="Product Trial Request Setup Wizard Completion Error")
			frappe.throw(f"Failed to complete Setup Wizard: {e}")
