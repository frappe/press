# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BackupBucket(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bucket_name: DF.Data | None
		cluster: DF.Link | None
		endpoint_url: DF.Data | None
		region: DF.Data | None
	# end: auto-generated types

	pass
