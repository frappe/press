"""Functions for automated audit of frappe cloud systems."""
import pprint
from datetime import datetime, timedelta
from typing import List

import frappe

from press.agent import Agent


class Audit:
	"""
	Base class for all types of Audit.

	`audit_type` member variable needs to be set to log
	"""

	def log(self, log, status="Success"):
		log = pprint.pformat(log)
		frappe.get_doc(
			{
				"doctype": "Audit Log",
				"log": log,
				"status": status,
				"audit_type": self.audit_type,
			}
		).insert()


class BenchFieldCheck(Audit):
	"""Audit to check fields of site in press are correct."""

	audit_type = "Bench Field Check"

	def __init__(self):
		servers = frappe.get_all("Server", pluck="name")
		log = {}
		status = "Success"
		for server in servers:
			agent = Agent(server)
			benches = agent.get("/benches")
			for bench_name, bench_desc in benches.items():
				sites_in_server = set(bench_desc["sites"])
				sites_in_press = set(
					frappe.get_all(
						"Site", {"bench": bench_name, "status": ("!=", "Archived")}, pluck="name"
					)
				)
				if sites_in_press != sites_in_server:
					status = "Failure"
					log[bench_name] = {
						"Sites on press only": list(sites_in_press.difference(sites_in_server)),
						"Sites on server only": list(sites_in_server.difference(sites_in_press)),
					}
		self.log(log, status)


class BackupRecordCheck(Audit):
	"""Check if latest automated backup records for sites are created."""

	audit_type = "Backup Record Check"
	interval = 24  # At least 1 automated backup a day
	site_list_key = f"Sites with no backup in {interval} hrs"

	def __init__(self):
		log = {self.site_list_key: []}
		status = "Success"
		for site in frappe.get_all("Site", {"status": "Active"}, pluck="name"):
			if not frappe.db.exists(
				"Site Backup",
				{
					"site": site,
					"owner": "Administrator",
					"creation": (">=", datetime.now() - timedelta(hours=self.interval)),
				},
			):
				status = "Failure"
				log[self.site_list_key].append(site)
		self.log(log, status)


class OffsiteBackupCheck(Audit):
	"""Check if files for offsite backup exists on the offsite backup provider."""

	audit_type = "Offsite Backup Check"
	list_key = "Offsite Backup Remote File unavailable in remote"

	def _get_all_files_in_s3(self) -> List[str]:
		all_files = []
		settings = frappe.get_single("Press Settings")
		s3 = settings.boto3_offsite_backup_session.resource("s3")
		for s3_object in s3.Bucket(settings.aws_s3_bucket).objects.all():
			all_files += s3_object.key
		return all_files

	def __init__(self):
		log = {self.list_key: []}
		status = "Success"
		all_files = self._get_all_files_in_s3()
		offsite_remote_files = frappe.db.sql(
			"""
			SELECT
				remote_file.name, remote_file.file_path, site_backup.site
			FROM
				`tabRemote File` remote_file
			JOIN
				`tabSite Backup` site_backup
			ON
				site_backup.site=remote_file.site
			WHERE
				site_backup.status="Success" and
				site_backup.files_availability="Available" and
				site_backup.offsite=True
			""",
			as_dict=True,
		)
		for remote_file in offsite_remote_files:
			if remote_file["file_path"] not in all_files:
				status = "Failure"
				log[self.list_key].append(remote_file)
		self.log(log, status)
