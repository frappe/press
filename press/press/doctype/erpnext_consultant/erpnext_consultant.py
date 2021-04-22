# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document
from frappe.utils import get_fullname


class ERPNextConsultant(Document):
	@property
	def full_name(self):
		return get_fullname(self.name)
