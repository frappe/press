# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document
from frappe.website.utils import cleanup_page_name


class MarketplaceAppCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		slug: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		self.slug = cleanup_page_name(self.name)
