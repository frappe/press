"""Functions for automated audit of frappe cloud systems."""
import json
from datetime import datetime, timedelta
from press.press.doctype.server.server import Server
from typing import List

import frappe

from press.agent import Agent


class Audit:
	"""
	Base class for all types of Audit.

	`audit_type` member variable needs to be set to log
	"""

	def log(self, log: dict, status: str):
		frappe.get_doc(
			{
				"doctype": "Audit Log",
				"log": json.dumps(log, indent=2),
				"status": status,
				"audit_type": self.audit_type,
			}
		).insert()


class BenchFieldCheck(Audit):
	"""Audit to check fields of site in press are correct."""

	audit_type = "Bench Field Check"

	def __init__(self):
		servers = Server.get_all_prod()
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
	list_key = f"Sites with no backup in {interval} hrs"

	def __init__(self):
		log = {self.list_key: []}
		interval_hrs_ago = datetime.now() - timedelta(hours=self.interval)
		tuples = frappe.db.sql(
			f"""
				SELECT
					site.name
				FROM
					`tabSite Backup` site_backup
				JOIN
					`tabSite` site
				ON
					site_backup.site = site.name
				WHERE
					site.status = "Active" and
					site_backup.owner = "Administrator" and
					site_backup.creation >= "{interval_hrs_ago}"
			"""
		)
		sites_with_backup_in_interval = set([t[0] for t in tuples])
		all_sites = set(
			frappe.get_all(
				"Site",
				{"status": "Active", "creation": ("<=", interval_hrs_ago), "is_standby": False},
				pluck="name",
			)
		)
		sites_without_backups = all_sites.difference(sites_with_backup_in_interval)
		if sites_without_backups:
			log[self.list_key] = list(sites_without_backups)
			self.log(log, "Failure")
		else:
			self.log(log, "Success")


class OffsiteBackupCheck(Audit):
	"""Check if files for offsite backup exists on the offsite backup provider."""

	audit_type = "Offsite Backup Check"
	list_key = "Offsite Backup Remote Files unavailable in remote"

	def _get_all_files_in_s3(self) -> List[str]:
		all_files = []
		settings = frappe.get_single("Press Settings")
		s3 = settings.boto3_offsite_backup_session.resource("s3")
		for s3_object in s3.Bucket(settings.aws_s3_bucket).objects.all():
			all_files.append(s3_object.key)
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
				site_backup.site = remote_file.site
			WHERE
				site_backup.status = "Success" and
				site_backup.files_availability = "Available" and
				site_backup.offsite = True
			""",
			as_dict=True,
		)
		for remote_file in offsite_remote_files:
			if remote_file["file_path"] not in all_files:
				status = "Failure"
				log[self.list_key].append(remote_file)
		self.log(log, status)


def check_bench_fields():
	BenchFieldCheck()

def check_backup_records(arg1):
	BackupRecordCheck()

def check_offsite_backups(arg1):
	OffsiteBackupCheck()
