# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from press.api.site import _new
from press.press.doctype.site.site import prepare_site
import frappe
from typing import List, Dict


class BackupRestorationTest(Document):
	doctype = "Backup Restoration Test"

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
		site_dict = prepare_site(self.site, with_files=False)
		server = frappe.get_value("Site", self.site, "server")
		try:
			site_job = _new(site_dict, server)
			self.test_site = site_job.get("site")
			self.save()
		except Exception:
			frappe.log_error("Site Creation Error")

	@classmethod
	def get_all_backup_restoration_tests(cls, filters: Dict) -> List[Document]:
		restoration_tests = frappe.get_all(cls.doctype, filters, pluck="name")
		return cls.get_docs(restoration_tests)

	@classmethod
	def get_docs(cls, names: List[str]) -> List[Document]:
		return [frappe.get_doc(cls.doctype, name) for name in names]


def update_from_site():
	filters = {"status": "Running"}
	running_restorations = BackupRestorationTest.get_all_backup_restoration_tests(filters)
	for restoration in running_restorations:
		site_status = frappe.db.get_value("Site", restoration.test_site, "status")
		status_map = {
			"Active": "Success",
			"Broken": "Failure",
			"Installing": "Running",
			"Pending": "Running",
		}
		restoration.status = status_map[site_status]
		restoration.save()


def update_from_site_archive():
	filters = {"archived": 0}
	unarchived_sites = BackupRestorationTest.get_all_backup_restoration_tests(filters)
	for unarchived_site in unarchived_sites:
		site_status = frappe.db.get_value("Site", unarchived_site.test_site, "status")
		unarchived_site.archived = 1 if site_status == "Archived" else 0
		unarchived_site.save()
