# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServerSnapshotSiteRecovery(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		database_backup_job: DF.Link | None
		database_name: DF.Data | None
		database_remote_file: DF.Link | None
		file_backup_job: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		private_remote_file: DF.Link | None
		public_remote_file: DF.Link | None
		site: DF.Data
		status: DF.Literal["Draft", "Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	pass
