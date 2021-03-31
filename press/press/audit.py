"""Functions for automated audit of frappe cloud systems."""
import pprint
from datetime import timedelta

import frappe

from press.agent import Agent


class Audit:
	"""Base class for all types of Audit."""

	def log(self, output, status="Success"):
		output = pprint.pformat(output)
		frappe.get_doc({"doctype": "Audit Log", "output": output, "status": status}).insert()


class BenchFieldCheck(Audit):
	"""Audit to check fields of site in press are correct."""

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
	"""Check if backup records for each site is created in regular intervals."""

	def __init__(self):
		sites_with_no_recent_backup = []
		for site in frappe.get_all("Site", {"status": "Active"}, pluck="name"):
			if not frappe.db.exists(
				"Site Backup",
				{"site": site, "owner": "Administrator", "creation": ("<", timedelta(hours=24))},
			):
				sites_with_no_recent_backup.append(site)
