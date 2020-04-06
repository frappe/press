# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document


class Plan(Document):
	def validate(self):
		if not self.period:
			frappe.throw("Period must be greater than 0")
