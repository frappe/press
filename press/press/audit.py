"""Functions for automated audit of frappe cloud systems."""
import pprint
from datetime import timedelta

import frappe

from press.agent import Agent


class Audit:
	"""
	Base class for all types of Audit.

	`audit_type` member variable needs to be set to log
	"""
		output = pprint.pformat(output)
		frappe.get_doc(
			{
				"doctype": "Audit Log",
				"output": output,
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

	def __init__(self):
		log = {}
		status = "Success"
		for site in frappe.get_all("Site", {"status": "Active"}, pluck="name"):
			if not frappe.db.exists(
				"Site Backup",
				{"site": site, "owner": "Administrator", "creation": ("<", timedelta(hours=24))},
			):
				status = "Failure"
				log[f"Sites with no backup in {self.interval} hrs"].append(site)
		self.log(log, status)
