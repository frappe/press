# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe


def execute():
	# Set `root_disk_size` to `disk_size`
	frappe.db.sql("UPDATE `tabVirtual Machine` SET `root_disk_size` = `disk_size`")

	# Set `disk_size` and `root_disk_size` on machines with multiple volumes
	multi_volume_machines = frappe.db.sql(
		"""
		SELECT machine.name
		FROM `tabVirtual Machine` machine
		LEFT JOIN `tabVirtual Machine Volume` volume
		ON volume.parent = machine.name
		WHERE machine.status in ('Running', 'Stopped', 'Pending')
		GROUP BY machine.name
		HAVING COUNT(volume.name) > 1
	""",
		as_dict=True,
	)
	for machine_name in multi_volume_machines:
		machine = frappe.get_doc("Virtual Machine", machine_name)
		machine.has_data_volume = True
		machine.save()
		disk_size = machine.get_data_volume().size
		root_disk_size = machine.get_root_volume().size
		frappe.db.set_value("Virtual Machine", machine.name, "disk_size", disk_size)
		frappe.db.set_value("Virtual Machine", machine.name, "root_disk_size", root_disk_size)
