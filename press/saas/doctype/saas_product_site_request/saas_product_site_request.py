# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.api.site import _new


class SaaSProductSiteRequest(Document):
	def create_site(self, subdomain):
		saas_product = frappe.get_doc('SaaS Product', self.saas_product)
		site = {
			'name': subdomain,
			'domain': saas_product.domain,
			'group': saas_product.release_group,
			'cluster': saas_product.cluster,
			'plan': saas_product.plan,
			'apps': [d.app for d in saas_product.apps],
		}
		data = _new(site)
		self.site = data["site"]
		self.status = "Wait for Site"
		self.save(ignore_permissions=True)
		return data

	def get_progress(self):
		job_name, status = frappe.db.get_value("Agent Job", {"site": self.site, "job_type": "New Site"}, ["name", "status"])
		if status == "Success":
			self.status = "Site Created"
			self.save(ignore_permissions=True)
			return {'progress': 100}
		elif status == "Running":
			steps = frappe.db.get_all("Agent Job Step", filters={"agent_job": job_name}, fields=["step_name", "status"], order_by="creation asc")
			done = [s for s in steps if s.status in ("Success", "Skipped", "Failure")]
			progress = len(done) / len(steps) * 100
			return {'progress': progress}
		elif status in ("Failure", "Undelivered"):
			return {'progress': 0, 'error': True}

		return {'progress': 0}
