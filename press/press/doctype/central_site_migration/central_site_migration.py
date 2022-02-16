# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.runner import Ansible
from press.utils import log_error

central_username = "central@frappecloud.com"
central_user_password = "wbFzfU62DALuQPZ"


def get_ongoing_migration(site: str, scheduled=False):
	ongoing_statuses = ["Pending", "Running"]
	if scheduled:
		ongoing_statuses.append("Scheduled")
	return frappe.db.exists(
		"Central Site Migration", {"site": site, "status": ("in", ongoing_statuses)}
	)


class CentralSiteMigration(Document):
	def before_insert(self):
		if get_ongoing_migration(self.site, scheduled=True):
			frappe.throw("Ongoing/Scheduled Site Migration for that site exists.")

	def after_insert(self):
		if not self.scheduled_time:
			self.start()

	@frappe.whitelist()
	def start(self):
		self.status = "Running"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_start", queue="short")

	def _start(self):
		try:
			ansible = Ansible(
				playbook="central-site-migration.yml",
				server=frappe.get_doc("Central Server", self.server),
				variables={
					"bench": self.bench,
					"site": self.site,
					"version": self.version,
					"username": central_username,
					"password": central_user_password,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Success"
			else:
				self.status = "Failure"
		except Exception:
			self.status = "Failure"
			log_error("Central Site Migration Exception", migration=self.as_dict())
		self.save()
