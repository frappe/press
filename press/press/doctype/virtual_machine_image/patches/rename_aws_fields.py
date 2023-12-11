# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Virtual Machine Image")
	rename_field("Virtual Machine Image", "aws_instance_id", "instance_id")
	rename_field("Virtual Machine Image", "aws_ami_id", "image_id")
	rename_field("Virtual Machine Image", "aws_snapshot_id", "snapshot_id")
