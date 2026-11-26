# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import frappe

from press.press.audit import get_benches_in_server
from press.press.doctype.server.server_monitoring import RAVEN_SERVER_ALERTS_CHANNEL
from press.utils.raven import send_raven_message

if TYPE_CHECKING:
	from press.press.doctype.site_backup.site_backup import SiteBackup

BATCH_SIZE = 50
BACKUP_SIZE_LIMIT = 2 * 1024 * 1024 * 1024  # 2 GB
# ponytail: one hardcoded owner; move to Press Settings if it changes
ALERT_MENTION = '<span data-id="shadrak@erpnext.com" data-type="userMention">@Shadrak</span>'


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
				cluster=("not in", frappe.get_all("Cluster", dict(status="Archived"), pluck="name")),
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

	def start(self) -> int:
		started = frappe.utils.now_datetime()
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
		# A failed site creation rolls back its test record, so count what is left
		return frappe.db.count("Backup Restoration Test", {"creation": (">=", started)})

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
		try:
			benches = get_benches_in_server(server)
		except Exception:
			# One unreachable agent must not stop the whole quarterly test
			frappe.log_error(
				"Backup Restoration Test: could not list benches",
				reference_doctype="Server",
				reference_name=server,
			)
			return []

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


def alert_backup_restoration_test_failure(text: str) -> None:
	send_raven_message(
		f"**Backup Restoration Test failed** {ALERT_MENTION}\n\n{text}", RAVEN_SERVER_ALERTS_CHANNEL
	)


def run_backup_restore_test():
	try:
		backup_restoration_test = BackupTest()
		created = backup_restoration_test.start()
	except Exception:
		alert_backup_restoration_test_failure("The quarterly job stopped. See the Scheduled Job Log.")
		raise

	picked = len(backup_restoration_test.sites)
	if not created or created < picked:
		alert_backup_restoration_test_failure(
			f"The job created {created} of {picked} tests. See the Error Log for *Site Creation Error*."
		)
