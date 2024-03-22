# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.site_config.site_config import Config


class CommonSiteConfig(Config):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		internal: DF.Check
		key: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		type: DF.Literal["", "String", "Password", "Number", "Boolean", "JSON"]
		value: DF.Code
	# end: auto-generated types

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		Config = frappe.qb.DocType("Common Site Config")
		query = query.where(Config.internal == 0).orderby(Config.key, order=frappe.qb.asc)
		configs = query.run(as_dict=True)
		return CommonSiteConfig.format_config_for_list(configs)
