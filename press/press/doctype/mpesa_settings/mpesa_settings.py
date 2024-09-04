# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt


from json import dumps, loads

import frappe
from frappe import _
from frappe.model.document import Document

class MpesaSettings(Document):
	supported_currencies = ["KES"]

	