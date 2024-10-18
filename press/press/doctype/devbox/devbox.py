# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document


class Devbox(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cpu_cores: DF.Int
		disk_mb: DF.Int
		ram: DF.Int
		server: DF.Link
		status: DF.Literal["Pending", "Starting", "Paused", "Running", "Archived", "Exited"]
	# end: auto-generated types
	pass

	@frappe.whitelist()
	def get_available_cpu_and_ram(self):	
		print("meow")

	@frappe.whitelist()
	def pull_latest_image(self):
		print("meow")




x