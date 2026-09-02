# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import json
from typing import ClassVar

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class Config(Document):
	dashboard_fields: ClassVar[list[str]] = ["key", "type", "value"]

	def get_type(self):
		return frappe.db.get_value("Site Config Key", self.key, "type")

	def format_config_for_list(configs):
		config_key_titles = frappe.db.get_all(
			"Site Config Key",
			fields=["key", "title"],
			filters={"key": ["in", [c.key for c in configs]]},
		)
		secret_keys = frappe.get_all("Site Config Key", filters={"type": "Password"}, pluck="key")
		for config in configs:
			if config.key in secret_keys:
				config.value = "*******"
			config.title = next((c.title for c in config_key_titles if c.key == config.key), "")
		return configs


class SiteConfig(Config):
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
		Config = frappe.qb.DocType("Site Config")
		query = query.where(Config.internal == 0)
		configs = query.run(as_dict=True)
		return SiteConfig.format_config_for_list(configs)


def parse_json_config_value(key: str, value):
	"""Config values of type JSON must be an object or an array.

	Anything else is stored as plain text and can't be read back as JSON, which breaks
	every subsequent save of the site. See decode_json_config_value.
	"""
	value = decode_json_config_value(key, value)
	if not isinstance(value, dict | list):
		frappe.throw(
			_("Value of <b>{0}</b> must be a JSON object or array, not a {1}").format(
				key, type(value).__name__
			)
		)
	return value


def decode_json_config_value(key: str, value):
	if isinstance(value, dict | list):
		return value
	try:
		return json.loads(cstr(value))
	except ValueError:
		frappe.throw(_("Value of <b>{0}</b> is not valid JSON: {1}").format(key, value))
