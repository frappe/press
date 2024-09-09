# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SiteAccessToken(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		site: DF.Link
		token: DF.Data
	# end: auto-generated types

	@staticmethod
	def generate(site: str) -> str:
		record = frappe.get_doc(
			{
				"doctype": "Site Access Token",
				"site": site,
				"token": frappe.generate_hash(length=32),
			}
		).insert(ignore_permissions=True)
		return f"{record.name}:{record.token}"


def cleanup_expired_access_tokens():
	# cleanup expired tokens
	frappe.db.sql(
		"""
		DELETE FROM `tabSite Access Token`
		WHERE TIMESTAMPDIFF(MINUTE, creation, NOW()) > 30
		"""
	)
	frappe.db.commit()
