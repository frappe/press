# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
import requests
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime
from frappe.utils.password import get_decrypted_password

from press.utils import convert_user_timezone_to_utc


class InspectTraceID(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		data: DF.Code | None
		trace_id: DF.Data
	# end: auto-generated types

	def load_from_db(self):
		frappe.only_for("Desk User")

	@frappe.whitelist()
	def fetch(self):
		frappe.only_for("Desk User")

		if not self.trace_id:
			return

		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if not log_server:
			return

		url = f"https://{log_server}/elasticsearch/filebeat-*/_search"
		password = get_decrypted_password("Log Server", log_server, "kibana_password")

		start_datetime = convert_user_timezone_to_utc(add_to_date(days=-30))
		end_datetime = convert_user_timezone_to_utc(now_datetime())

		query = {
			"query": {
				"bool": {
					"filter": [
						{"match_phrase": {"json.uuid": self.trace_id}},
						{"range": {"@timestamp": {"gt": start_datetime, "lte": end_datetime}}},
					],
				}
			},
			"size": 1,
		}

		response = requests.post(url, json=query, auth=("frappe", password)).json()
		records = response.get("hits", {}).get("hits", [])
		self.data = frappe.as_json(records[0] if records else "")

	# Not relevant
	def db_update(self):
		raise NotImplementedError

	def delete(self):
		raise NotImplementedError

	def db_insert(self, *args, **kwargs):
		raise NotImplementedError

	@staticmethod
	def get_list(filters=None, page_length=20, **kwargs):
		pass

	@staticmethod
	def get_count(filters=None, **kwargs):
		pass

	@staticmethod
	def get_stats(**kwargs):
		pass
