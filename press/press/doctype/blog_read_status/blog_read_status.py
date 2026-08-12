# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import today


class BlogReadStatus(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		last_read_blog: DF.Data | None
		last_reviewed_on: DF.Date | None
		user: DF.Link
	# end: auto-generated types

	def mark_read(self, blog: str):
		self.last_read_blog = blog
		self.last_reviewed_on = today()
		self.save(ignore_permissions=True)

	def mark_reviewed(self):
		self.last_reviewed_on = today()
		self.save(ignore_permissions=True)

	def has_read(self, blog: str) -> bool:
		return self.last_read_blog == blog


def get_blog_read_status(user: str) -> BlogReadStatus:
	if frappe.db.exists("Blog Read Status", user):
		return frappe.get_doc("Blog Read Status", user)

	return frappe.get_doc(doctype="Blog Read Status", user=user).insert(ignore_permissions=True)


def has_read_blog(user: str, blog: str) -> bool:
	return frappe.db.get_value("Blog Read Status", user, "last_read_blog", cache=True) == blog
