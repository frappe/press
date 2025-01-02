# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe


def execute():
	# Set `root_size` to size`
	frappe.db.sql("UPDATE `tabVirtual Machine Image` SET `root_size` = `size`")

	# Set `disk_size` and `root_disk_size` on images with multiple volumes
	multi_volume_images = frappe.db.sql(
		"""
		SELECT image.name
		FROM `tabVirtual Machine Image` image
		LEFT JOIN `tabVirtual Machine Image Volume` volume
		ON volume.parent = image.name
		WHERE image.status = 'Available'
		GROUP BY image.name
		HAVING COUNT(volume.name) > 1
	""",
		as_dict=True,
	)
	for image_name in multi_volume_images:
		image = frappe.get_doc("Virtual Machine Image", image_name)
		image.has_data_volume = True
		image.save()
		size = image.get_data_volume().size
		root_size = image.get_root_volume().size
		frappe.db.set_value("Virtual Machine Image", image.name, "size", size)
		frappe.db.set_value("Virtual Machine Image", image.name, "root_size", root_size)
