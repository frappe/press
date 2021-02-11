# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from press.agent import Agent
from press.utils import log_error


def collect():
	benches = frappe.get_all(
		"Bench", fields=["name", "server"], filters={"status": "Active"}
	)
	for bench in benches:
		agent = Agent(bench.server)
		logs = agent.fetch_monitor_data(bench.name)
		for log in logs:
			try:
				doc = {
					"name": log["uuid"],
					"site": log["site"],
					"timestamp": log["timestamp"],
					"duration": log["duration"],
				}

				if log["transaction_type"] == "request":
					doc.update(
						{
							"doctype": "Site Request Log",
							"url": log["request"]["path"],
							"ip": log["request"]["ip"],
							"http_method": log["request"]["method"],
							"length": log["request"]["response_length"],
							"status_code": log["request"]["status_code"],
							"reset": log["request"].get("reset"),
							"counter": log["request"].get("counter"),
						}
					)
				elif log["transaction_type"] == "job":
					doc.update(
						{
							"doctype": "Site Job Log",
							"job_name": log["job"]["method"],
							"scheduled": log["job"]["scheduled"],
							"wait": log["job"]["wait"] / 1000,
							"duration": log["duration"] / 1000,
						}
					)
				frappe.get_doc(doc).db_insert()
			except frappe.exceptions.DuplicateEntryError:
				pass
			except Exception:
				log_error("Agent Analytics Collection Exception", log=log, doc=doc)
