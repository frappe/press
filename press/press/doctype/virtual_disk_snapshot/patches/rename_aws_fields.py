# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Virtual Disk Snapshot")
	rename_field("Virtual Disk Snapshot", "aws_snapshot_id", "snapshot_id")
