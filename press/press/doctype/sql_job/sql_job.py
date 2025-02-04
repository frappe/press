# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class SQLJob(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.sql_job_query.sql_job_query import SQLJobQuery

		allow_any_query: DF.Check
		allow_ddl: DF.Check
		committed: DF.Check
		database_name: DF.Data
		job: DF.Link | None
		job_type: DF.Data
		lock_wait_timeout: DF.Int
		max_statement_time: DF.Int
		profile_query: DF.Check
		queries: DF.Table[SQLJobQuery]
		read_only: DF.Check
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		target_document: DF.DynamicLink
		target_type: DF.Link
		user_type: DF.Literal["Root User", "Site User"]
		wait_timeout: DF.Int
	# end: auto-generated types

	pass
