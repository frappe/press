# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.saas.doctype.saas_product.saas_product import SaaSProduct
from press.press.doctype.site.site import Site
from press.api.client import dashboard_whitelist


class SaaSProductSiteRequest(Document):
	dashboard_fields = ["site", "status", "saas_product"]

	@dashboard_whitelist()
	def create_site(self, plan, cluster=None):
		product: SaaSProduct = frappe.get_doc("SaaS Product", self.saas_product)
		site: Site = product.setup_trial_site(self.team, cluster)
		user = self.get_user_details()
		agent_job = site.create_user(user.email, user.first_name, user.last_name)
		self.agent_job = agent_job.name
		site.create_subscription(plan)
		site.reload()
		trial_days = (
			frappe.db.get_value("SaaS Product", self.saas_product, "trial_days") or 14
		)
		site.trial_end_date = frappe.utils.add_days(None, trial_days)
		# update_config implicitly calles site.save
		site.flags.ignore_permissions = True
		site.update_site_config(
			{
				"subscription": {"trial_end_date": site.trial_end_date.strftime("%Y-%m-%d")},
				"app_include_js": ["https://frappecloud.com/saas/subscription.js"],
			}
		)
		# site.save(ignore_permissions=True)
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
		job_name, status = frappe.db.get_value(
			"Agent Job",
			filters,
			["name", "status"],
		)
		if status == "Success":
			self.status = "Site Created"
			self.save(ignore_permissions=True)
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
				progress = current_progress + 1
			return {"progress": progress}
		elif status == "Failure":
			self.status = "Error"
			self.save(ignore_permissions=True)
			return {"progress": current_progress, "error": True}
		elif status == "Undelivered":
			return {"progress": current_progress, "error": True}

		return {"progress": current_progress + 1}
