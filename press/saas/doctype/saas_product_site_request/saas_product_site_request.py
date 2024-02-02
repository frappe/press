# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.saas.doctype.saas_product.pooling import SitePool


class SaaSProductSiteRequest(Document):
	dashboard_fields = ["site", "status", "saas_product"]
	dashboard_actions = ["create_site", "get_progress", "get_login_sid"]

	def get_doc(self, doc):
		saas_product = frappe.db.get_value(
			"SaaS Product",
			{"name": self.saas_product},
			["name", "title", "logo", "domain", "description"],
			as_dict=True,
		)
		saas_product.description = frappe.utils.md_to_html(saas_product.description)
		doc.saas_product = saas_product
		return doc

	@frappe.whitelist()
	def create_site(self, subdomain, plan):
		pool = SitePool(self.saas_product)
		site = pool.create_or_rename(subdomain, self.team, self.account_request)
		site.create_subscription(plan)
		site.reload()
		site.trial_end_date = frappe.utils.add_days(None, 14)
		site.save(ignore_permissions=True)
		self.site = site.name
		self.status = "Wait for Site"
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def get_login_sid(self):
		email = frappe.db.get_value("Account Request", self.account_request, "email")
		return frappe.get_doc("Site", self.site).get_login_sid(user=email)

	@frappe.whitelist()
	def get_progress(self, current_progress=None):
		current_progress = current_progress or 0
		job_name, status = frappe.db.get_value(
			"Agent Job",
			{"site": self.site, "job_type": ["in", ["New Site", "Rename Site"]]},
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
		elif status in ("Failure", "Undelivered"):
			return {"progress": current_progress, "error": True}

		return {"progress": current_progress + 1}
