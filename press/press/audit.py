"""Functions for automated audit of frappe cloud systems."""
import pprint

import frappe

from press.agent import Agent


class Audit:
	"""Base class for all types of Audit."""

	def log(self, output):
		output = pprint.pformat(output)
		frappe.get_doc({"doctype": "Audit Log", "output": output}).insert()


class BenchFieldCheck(Audit):
	"""Audit to check fields of site in press are correct."""

	def __init__(self):
		servers = frappe.get_all("Server", pluck="name")
		log = {}
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
					log[bench_name] = {
						"press": list(sites_in_press.difference(sites_in_server)),
						"server": list(sites_in_server.difference(sites_in_press)),
					}
		self.log(log)
