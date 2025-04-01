# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import typing

import frappe
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from press.press.doctype.server.server import Server


class Snapshots(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Data
		dump: DF.JSON | None
		server: DF.Data
	# end: auto-generated types

	def after_insert(self):
		server: Server = frappe.get_doc("Server", self.server)
		self.dump = json.dumps(server.agent.get_snapshot(self.bench), indent=2)
		self.save()
