# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Virtual Machine")
	rename_field("Virtual Machine", "aws_subnet_id", "subnet_id")
