# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.caching import redis_cache


class CloudProvider(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		image: DF.AttachImage
		title: DF.Data
	# end: auto-generated types

	pass


@redis_cache(ttl=60)
def get_cloud_providers() -> dict[str, dict]:
	data = frappe.get_all(
		"Cloud Provider",
		fields=["name", "title", "image"],
	)
	return {d.name: d for d in data}
