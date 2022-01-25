# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document
from frappe.website.utils import cleanup_page_name


class MarketplaceAppCategory(Document):
	def before_insert(self):
		self.slug = cleanup_page_name(self.name)
