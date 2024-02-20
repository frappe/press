# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from press.press.audit import get_benches_in_server
from press.press.doctype.server.server import Server
from typing import List
from random import choice

import frappe


class BackupTest:
	def __init__(self) -> None:
		self.trial_plans = frappe.get_all(
			"Site Plan", dict(enabled=1, is_trial_plan=1), pluck="name"
		)
		self.sites = self.get_random_sites()

	def get_random_sites(self) -> List:
		sites = []
		servers = Server.get_all_primary_prod()
		for server in servers:
			benches = self.get_benches(server)
			for bench in benches:
				site_list = frappe.get_all(
					"Site",
					dict(status="Active", plan=("not in", self.trial_plans), bench=bench),
					pluck="name",
				)
				if not site_list:
					continue
				site = choice(site_list)
				sites.append(site)

		return sites

	def start(self):
		for site in self.sites:
			try:
				frappe.get_doc(
					{
						"doctype": "Backup Restoration Test",
						"date": frappe.utils.now_datetime(),
						"site": site,
						"status": "Running",
					}
				).insert()
			except Exception:
				frappe.log_error("Backup Restore Test insertion failed")

	def get_benches(self, server: str) -> List[str]:
		benches = get_benches_in_server(server)

		# select all benches from central benches
		# TODO: provision to run for all release groups
		groups = frappe.get_all(
			"Release Group", dict(enabled=1, central_bench=1), pluck="name"
		)

		bench_list = []
		for group in groups:
			group_benches = frappe.get_all(
				"Bench", dict(status="Active", group=group, server=server), pluck="name"
			)

			for bench in benches.keys():
				if bench in group_benches:
					bench_list.append(bench)

		return bench_list


def archive_backup_test_sites():
	backup_tests = frappe.get_all(
		"Backup Restoration Test",
		dict(status=("in", ("Archive Failed", "Success"))),
		pluck="test_site",
	)
	if backup_tests:
		for test_site in backup_tests:
			site = frappe.get_doc("Site", test_site)
			if site.status == "Active":
				site.archive(reason="Backup Restoration Test")


def run_backup_restore_test():
	backup_restoration_test = BackupTest()
	backup_restoration_test.start()
