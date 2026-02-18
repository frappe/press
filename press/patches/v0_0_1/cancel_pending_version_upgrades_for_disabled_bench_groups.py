# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe


def execute():
	upgrades = frappe.get_all(
		"Version Upgrade",
		filters={
			"deploy_private_bench": 1,
			"status": ("in", ["Pending"]),
		},
		fields=["name", "site_update", "destination_group"],
	)
	for upgrade in upgrades:
		destination_group = upgrade.destination_group
		if destination_group and not upgrade.site_update:
			rg_enabled = frappe.db.get_value("Release Group", destination_group, "enabled")
			if not rg_enabled:
				frappe.db.set_value("Version Upgrade", upgrade.name, "status", "Cancelled")
				continue
