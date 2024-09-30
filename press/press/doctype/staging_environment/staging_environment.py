# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StagingEnvironment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		expiry_time: DF.Datetime
		site: DF.Link
		site_backup: DF.Link | None
		site_creation_method: DF.Literal["New Site", "Restore From Backup"]
		staging_release_group: DF.Link
		staging_site: DF.Link | None
		team: DF.Link
	# end: auto-generated types

	pass
