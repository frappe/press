# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


from frappe.core.doctype.file.file import create_new_folder


def execute():
	create_new_folder("Backup Uploads", "Home")
