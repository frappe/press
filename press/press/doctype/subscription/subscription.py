# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Subscription(Document):
	def validate(self):
		if self.status == "Active":
			for subscription in frappe.get_all("Subscription",
					{"status": "Active", 'name': ["!=", self.name]}):

				frappd.db.set_value("Subscription", subscription.name, 'status', 'Completed')

