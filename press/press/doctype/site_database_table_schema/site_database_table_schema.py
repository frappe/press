# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.agent import Agent

if TYPE_CHECKING:
	from press.press.doctype.site_migration.site_migration import AgentJob


class SiteDatabaseTableSchema(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_job: DF.Link | None
		schema_json: DF.LongText
		site: DF.Link
	# end: auto-generated types

	def fetch(self, reload=False) -> tuple[bool, dict]:
		"""
		This function will return the schema of the database table

		Args:
			reload: bool - if True, it will fetch the schema from the server again

		Returns:
				tuple[bool, list]
				-  1st element: bool - Loading status
				-  2nd element: dict - Dictionary of table schemas
					Example -
					{
						"__Auth": [
							{
								"column": "doctype",
								"data_type": "varchar",
								"default": "NULL",
								"indexes": [
									"PRIMARY"
								],
								"is_nullable": false
							},
							....
						],
						....
					}
		"""
		if len(self.schema) > 0 and not reload:
			return False, self.schema

		if self.agent_job is not None and frappe.get_value("Agent Job", self.agent_job, "status") in [
			"Undelivered",
			"Pending",
			"Running",
		]:
			return True, {}

		self.schema_json = "{}"
		site = frappe.get_doc("Site", self.site)
		self.agent_job = Agent(site.server).fetch_database_table_schema(site).name
		self.save(ignore_permissions=True)

		return True, {}

	@property
	def last_updated(self) -> str:
		return self.modified or self.creation

	@property
	def schema(self) -> dict:
		try:
			return json.loads(self.schema_json)
		except frappe.DoesNotExistError:
			return {}

	@staticmethod
	def process_job_update(job: "AgentJob"):
		if job.status != "Success":
			return
		response_data = json.loads(job.data) or {}
		if response_data and frappe.db.exists("Site Database Table Schema", {"site": job.site}):
			doc = frappe.get_doc("Site Database Table Schema", {"site": job.site})
			doc.schema_json = json.dumps(response_data)
			doc.save(ignore_permissions=True)
