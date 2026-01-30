# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.caching import redis_cache


class ServerPlanType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText
		order_in_list: DF.Int
		title: DF.Data
	# end: auto-generated types

	pass


@redis_cache(ttl=60)
def get_server_plan_types() -> dict[str, dict]:
	data = frappe.get_all(
		"Server Plan Type",
		fields=["name", "title", "description", "order_in_list"],
		order_by="order_in_list desc",
	)
	return {d.name: d for d in data}
