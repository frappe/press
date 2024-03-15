# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CloudRegion(Document):
	@staticmethod
	def get_cloud_regions():
		"""Return the list of regions"""
		cloud_regions = {}

		for cloud_provider in ["OCI", "AWS EC2"]:
			cloud_regions[cloud_provider] = frappe.get_all(
				"Cloud Region",
				filters={"provider": cloud_provider},
				fields=["name"],
				pluck="name",
			)

		return cloud_regions
