# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import get_fullname


class ERPNextConsultant(Document):
	@property
	def full_name(self):
		return get_fullname(self.name)

	@classmethod
	def list_for_region(cls, region_name: str) -> [str]:
		"""List ACTIVE consultants for a region."""
		return frappe.db.sql_list(
			f"""
				SELECT
					consultant.name
				FROM
					`tabERPNext Consultant` consultant
				JOIN
					`tabERPNext Consultant Region` region
				ON
					region.parent = consultant.name
				WHERE
					consultant.active = True and
					region.territory = "{region_name}"
			"""
		)

	@classmethod
	def _get_one_for_region(cls, region_name: str) -> str:
		"""Get consultant for a region other than the one last allocated."""
		consultants = cls.list_for_region(region_name)
		region = frappe.get_cached_doc("Region", region_name)
		try:
			return consultants[consultants.index(region.last_allocated_to) + 1]
		except (IndexError, ValueError):
			return consultants[0]
		except IndexError:
			return ""

	@classmethod
	def get_one_for_country(cls, country: str) -> str:
		"""
		Try to get next consultant for a country in round robin fashion.

		Return blank if none.
		"""
		try:
			region = frappe.db.get_value("Country", country, "region")
			erpnext_consultant = cls._get_one_for_region(region)
			frappe.db.set_value("Region", region, "last_allocated_to", erpnext_consultant)
			return erpnext_consultant
		except Exception:
			return ""
