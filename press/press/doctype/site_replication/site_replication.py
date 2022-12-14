# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.press.doctype.site.site import prepare_site
from press.api.site import _new
from typing import List


class SiteReplication(Document):
	doctype = "Site Replication"

	def before_insert(self):
		domain = frappe.db.get_single_value("Press Settings", "domain")
		self.new_site = self.subdomain + domain

	def validate(self):
		self.validate_duplicate()  # check for already running site replication
		self.validate_site_name()  # check if there is an non-archived site with same name

	def validate_duplicate(self):
		site_reps = frappe.get_all(
			"Site Replication",
			dict(site=self.site, subdomain=self.subdomain, status="Running"),
			pluck="name",
		)
		if site_reps:
			frappe.throw(f"Site Replication for {self.site} is already running.")

	def validate_site_name(self):
		sites = frappe.get_all(
			"Site", dict(status=["!=", "Archived"], name=self.new_site), pluck="name"
		)

		if sites:
			frappe.throw(
				f"Site {self.new_site} already exists. Please choose another subdomain."
			)

	def after_insert(self):
		self.status = "Running"
		site_dict = prepare_site(self.site, self.subdomain)
		try:
			site_job = _new(site_dict, self.server)
			self.new_site = site_job.get("site")
		except Exception:
			frappe.log_error("Site Replication Error")

	@classmethod
	def get_all_running_site_replications(cls) -> List[Document]:
		replications = frappe.get_all(cls.doctype, dict(status="Running"), pluck="name")
		return cls.get_docs(replications)

	@classmethod
	def get_docs(cls, names: List[str]) -> List[Document]:
		return [frappe.get_doc(cls.doctype, name) for name in names]


def update_from_site():
	ongoing_replications = SiteReplication.get_all_running_site_replications()
	for replication in ongoing_replications:
		site_doc = frappe.get_doc("Site", replication.new_site)
		site_status = {
			"Broken": "Failure",
			"Active": "Success",
			"Pending": "Running",
			"Installing": "Running",
		}
		replication.status = site_status[site_doc.status]
		replication.save()
