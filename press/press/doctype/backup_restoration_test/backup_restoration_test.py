# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from press.api.site import _new
from press.press.doctype.site.site import prepare_site
import frappe


class BackupRestorationTest(Document):
	def before_insert(self):
		self.new_sitename = "brt-" + str(self.site)

	def validate(self):
		self.check_duplicate_test()
		self.check_duplicate_active_site()

	def after_insert(self):
		self.create_test_site()

	def check_duplicate_test(self):
		# check if another backup restoration is already running
		backups = frappe.get_all(
			"Backup Restoration Test",
			dict(status=("in", ["Running", "Started"]), site=self.site, name=("!=", self.name)),
			pluck="name",
		)
		if backups:
			frappe.throw(f"Backup Restoration Test for {self.site} is already running.")

	def check_duplicate_active_site(self):
		# check if any active backup restoration test site is active
		sites = frappe.get_all(
			"Site", dict(status="Active", name=self.test_site), pluck="name"
		)
		if sites:
			frappe.throw(
				f"Site {self.test_site} is already active. Please archive the site first."
			)

	def create_test_site(self) -> None:
		self.status = "Running"
		site_dict = prepare_site(self.site)
		server = frappe.get_value("Site", self.site, "server")
		try:
			site_job = _new(site_dict, server, True)
			self.test_site = site_job.get("site")
			self.save()
		except Exception:
			frappe.log_error("Site Creation Error")
