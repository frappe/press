# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doctype("App Patch")

	# All archived benches
	Bench = frappe.qb.DocType("Bench")
	bench_names = (
		frappe.qb.from_(Bench).select(Bench.name).where(Bench.status == "Archived").run(pluck="name")
	)

	# All app patches which have those benches with the applied status
	frappe.db.set_value(
		"App Patch", {"bench": ["in", bench_names], "status": "Applied"}, "status", "Archived"
	)
	frappe.db.commit()
