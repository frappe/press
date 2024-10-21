# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

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
		domain: DF.Link | None
		initialized: DF.Check
		ram: DF.Int
		server: DF.Link
		status: DF.Literal["Pending", "Starting", "Paused", "Running", "Archived", "Exited"]
		subdomain: DF.Data
	# end: auto-generated types
	pass

	def _get_devbox_name(self, subdomain: str):
		"""Get full devbox domain name given subdomain."""
		if not self.domain:
			self.domain = frappe.db.get_single_value("Press Settings", "domain")
		return f"{subdomain}.{self.domain}"

	def autoname(self):
		self.name = self._get_devbox_name(subdomain=self.subdomain)

	@frappe.whitelist()
	def get_available_cpu_and_ram(self):
		print("meow")

	@frappe.whitelist()
	def pull_latest_image(self):
		print("meow")
