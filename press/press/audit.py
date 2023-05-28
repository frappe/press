"""Functions for automated audit of frappe cloud systems."""
import json
from datetime import datetime, timedelta
from press.press.doctype.server.server import Server
from typing import Dict, List
from frappe.utils import rounded

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


def get_benches_in_server(server: str) -> List[Dict]:
	agent = Agent(server)
	return agent.get("/benches")


class BenchFieldCheck(Audit):
	"""Audit to check fields of site in press are correct."""

	audit_type = "Bench Field Check"
	server_map = {}
	press_map = {}

	def __init__(self):
		log = {}
		status = "Success"

		self.generate_server_map()
		self.generate_press_map()

		log = {
			"Summary": None,
			"potential_fixes": {},
			"sites_only_on_press": self.get_sites_only_on_press(),
			"sites_only_on_server": self.get_sites_only_on_server(),
			"sites_on_multiple_benches": self.get_sites_on_multiple_benches(),
		}
		if any(log.values()):
			status = "Failure"

		log["potential_fixes"] = self.get_potential_fixes()
		log["Summary"] = {
			"Potential fixes": sum(len(sites) for sites in log["potential_fixes"].values()),
			"Sites only on press": len(log["sites_only_on_press"]),
			"Sites only on server": len(log["sites_only_on_server"]),
			"Sites on multiple benches": len(log["sites_on_multiple_benches"]),
		}
		self.apply_potential_fixes()

		self.log(log, status)

	def generate_server_map(self):
		servers = Server.get_all_primary_prod()
		for server in servers:
			benches = get_benches_in_server(server)
			if not benches:
				continue
			for bench_name, bench_desc in benches.items():
				for site in bench_desc["sites"]:
					self.server_map.setdefault(site, []).append(bench_name)

	def generate_press_map(self):
		frappe.db.commit()
		sites = frappe.get_all("Site", ["name", "bench"], {"status": ("!=", "Archived")})
		self.press_map = {site.name: site.bench for site in sites}

	def get_sites_only_on_press(self):
		sites = []
		for site, bench in self.press_map.items():
			if site not in self.server_map:
				sites.append(site)
		return sites

	def get_sites_only_on_server(self):
		sites = {}
		for site, benches in self.server_map.items():
			if site not in self.press_map:
				sites[site] = benches[0] if len(benches) == 1 else benches
		return sites

	def get_sites_on_multiple_benches(self):
		sites = {}
		for site, benches in self.server_map.items():
			if len(benches) > 1:
				sites[site] = benches
		return sites

	def get_potential_fixes(self):
		def bench_field_updates():
			fixes = {}
			for site, bench in self.press_map.items():
				server_benches = self.server_map.get(site, [])
				if len(server_benches) == 1 and server_benches[0] != bench:
					fixes[site] = (bench, server_benches[0])
			return fixes

		return {"bench_field_updates": bench_field_updates()}

	def apply_potential_fixes(self):
		fixes = self.get_potential_fixes()
		for site, benches in fixes["bench_field_updates"].items():
			frappe.db.set_value("Site", site, "bench", benches[1])
		frappe.db.commit()


class AppServerReplicaDirsCheck(Audit):

	audit_type = "App Server Replica Dirs Check"

	def __init__(self):
		log = {}
		status = "Success"
		replicas_and_primary = frappe.get_all(
			"Server", {"is_replication_setup": True}, ["name", "primary"], as_list=True
		)
		for replica, primary in replicas_and_primary:
			replica_benches = get_benches_in_server(replica)
			primary_benches = get_benches_in_server(primary)
			for bench, bench_desc in primary_benches.items():
				replica_bench_desc = replica_benches.get(bench)
				if not replica_bench_desc:
					status = "Failure"
					log[bench] = {"Sites on primary only": bench_desc["sites"]}
					continue

				sites_on_primary_only = list(
					set(bench_desc["sites"]) - set(replica_bench_desc["sites"])
				)
				if sites_on_primary_only:
					status = "Failure"
					log[bench] = {"Sites on primary only": sites_on_primary_only}
		self.log(log, status)


class BackupRecordCheck(Audit):
	"""Check if latest automated backup records for sites are created."""

	audit_type = "Backup Record Check"
	interval = 24  # At least 1 automated backup a day
	list_key = f"Sites with no backup in {interval} hrs"
	backup_summary = "Backup Summary"

	def __init__(self):
		log = {self.list_key: [], self.backup_summary: {}}
		interval_hrs_ago = datetime.now() - timedelta(hours=self.interval)
		trial_plans = tuple(frappe.get_all("Plan", dict(is_trial_plan=1), pluck="name"))
		cond_filters = " AND site.plan NOT IN {trial_plans}" if trial_plans else ""
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
					site_backup.creation >= "{interval_hrs_ago}
					{cond_filters}"
			"""
		)
		sites_with_backup_in_interval = set([t[0] for t in tuples])
		filters = {
			"status": "Active",
			"creation": ("<=", interval_hrs_ago),
			"is_standby": False,
		}
		if trial_plans:
			filters.update({"plan": ("not in", trial_plans)})
		all_sites = set(
			frappe.get_all(
				"Site",
				filters=filters,
				pluck="name",
			)
		)
		sites_without_backups = all_sites.difference(sites_with_backup_in_interval)

		try:
			success_rate = (len(sites_with_backup_in_interval) / len(all_sites)) * 100
		except ZeroDivisionError:
			success_rate = 0
		summary = {
			"Successful Backups": len(sites_with_backup_in_interval),
			"Failed Backups": len(sites_without_backups),
			"Total Active Sites": len(all_sites),
			"Success Rate": rounded(success_rate, 1),
		}
		log[self.backup_summary] = summary

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


class UnbilledSubscriptionsCheck(Audit):
	"""Checks daily for enabled/valid subscriptions that don't have any usage records created"""

	audit_type = "Unbilled Subscription Check"
	list_key = "Subscriptions with no usage records created"

	def __init__(self):
		log = {self.list_key: []}
		status = "Success"
		subscriptions = self.subscriptions_without_usage_record()
		log[self.list_key] += subscriptions
		status = "Failure" if len(subscriptions) > 0 else "Success"
		self.log(log, status)

	def subscriptions_without_usage_record(self):
		from press.press.doctype.subscription.subscription import (
			paid_plans,
			sites_with_free_hosting,
			created_usage_records,
		)

		free_sites = sites_with_free_hosting()
		# valid susbcriptions without UR for today
		return frappe.db.get_all(
			"Subscription",
			filters={
				"enabled": True,
				"plan": ("in", paid_plans()),
				"name": ("not in", created_usage_records(free_sites, frappe.utils.today())),
				"document_name": ("not in", free_sites),
			},
			pluck="name",
		)


def check_bench_fields():
	BenchFieldCheck()


def check_backup_records():
	BackupRecordCheck()


def check_offsite_backups():
	OffsiteBackupCheck()


def check_app_server_replica_benches():
	AppServerReplicaDirsCheck()


def check_unbilled_subscriptions():
	UnbilledSubscriptionsCheck()
