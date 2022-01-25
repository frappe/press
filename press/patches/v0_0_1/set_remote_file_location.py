# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.desk.doctype.tag.tag import add_tag


def execute():
	frappe.reload_doc("press", "doctype", "remote_file")
	remote_files = (
		x["name"] for x in frappe.get_all("Remote File", [["bucket", "like", ""]])
	)
	uploads_bucket = frappe.db.get_single_value("Press Settings", "remote_uploads_bucket")

	for remote_file in remote_files:
		frappe.db.set_value("Remote File", remote_file, "bucket", uploads_bucket)
		add_tag("Site Upload", "Remote File", remote_file)

	frappe.db.commit()
