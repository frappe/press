# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class DeployCandidateDifferenceApp(Document):
	dashboard_fields = ["difference", "app"]
