# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import frappe

from press.press.audit import get_benches_in_server

if TYPE_CHECKING:
	from press.press.doctype.site_backup.site_backup import SiteBackup

BATCH_SIZE = 50
BACKUP_SIZE_LIMIT = 2 * 1024 * 1024 * 1024  # 2 GB


class BackupTest:
	def __init__(self) -> None:
		self.trial_plans = frappe.get_all("Site Plan", dict(enabled=1, is_trial_plan=1), pluck="name")
		self.sites = self.get_random_sites()

	def get_random_sites(self) -> list:
		sites: list[str] = []
		servers = frappe.get_all(
			"Server",
			dict(
				status="Active",
				public=True,
				is_primary=True,
			),
			pluck="name",
		)
		random.shuffle(servers)
		for server in servers:
			benches = self.get_benches(server)
			for bench in benches:
				site_list: list[str] = frappe.get_all(
					"Site",
					dict(status="Active", plan=("not in", self.trial_plans), bench=bench),
					pluck="name",
				)
				if not site_list:
					continue
				random.shuffle(site_list)
				chosen_site = None
				for site in site_list:
					if self.is_last_backup_size_less_than_limit(site):
						chosen_site = site
						break
				if chosen_site:
					sites.append(chosen_site)
					break

			if len(sites) >= BATCH_SIZE:
				break

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

	def is_last_backup_size_less_than_limit(self, site: str) -> bool:
		try:
			backup: SiteBackup = frappe.get_last_doc(
				"Site Backup",
				{
					"site": site,
					"with_files": True,
					"offsite": True,
					"status": "Success",
					"files_availability": "Available",
				},
			)
		except frappe.DoesNotExistError:
			return False
		else:
			db_size, public_size, private_size = (
				frappe.get_doc("Remote File", file_name).size if file_name else 0
				for file_name in (
					backup.remote_database_file,
					backup.remote_public_file,
					backup.remote_private_file,
				)
			)
			if any(size > BACKUP_SIZE_LIMIT for size in (db_size, public_size, private_size)):
				return False
			return True

	def get_benches(self, server: str) -> list[str]:
		benches = get_benches_in_server(server)

		# select all benches from central benches
		# TODO: provision to run for all release groups
		groups = frappe.get_all("Release Group", dict(enabled=1, public=1), pluck="name")

		bench_list = []
		for group in groups:
			group_benches = frappe.get_all(
				"Bench", dict(status="Active", group=group, server=server), pluck="name"
			)

			for bench in benches:
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
