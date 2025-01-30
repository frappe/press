# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document
from frappe.model.naming import make_autoname


class DevboxImage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		image_id: DF.Data | None
		image_name: DF.Data | None
		image_reference: DF.Data | None
		image_tag: DF.Data
		namespace: DF.Data
		registry_domain: DF.Data
	# end: auto-generated types
	pass

	def autoname(self):
		series = "devbox-image-.######"
		self.name = make_autoname(series)

	def before_save(self):
		self.image_reference = f"{self.registry_domain}/{self.namespace}/{self.image_name}:{self.image_tag}"
