# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import typing

import frappe
import requests
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server


class ProcessSnapshot(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Link
		dump: DF.JSON | None
		server: DF.Link
	# end: auto-generated types

	def check_bench_on_server(self):
		if not frappe.get_value("Bench", {"name": self.bench, "server": self.server}):
			frappe.throw(f"{self.bench} does not exist on server {self.server}")

	def validate(self):
		self.check_bench_on_server()

	def after_insert(self):
		server: Server = frappe.get_doc("Server", self.server)
		try:
			self.dump = json.dumps(server.agent.get_snapshot(self.bench), indent=2)
		except requests.exceptions.HTTPError as e:
			self.dump = json.dumps({"error": str(e)}, indent=2)
		self.save()
