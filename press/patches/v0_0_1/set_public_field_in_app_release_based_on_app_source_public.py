# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "app_release")
	frappe.db.sql(
		"""
		UPDATE `tabApp Release` as `release`
		INNER JOIN `tabApp Source` as source
		ON `release`.source = `source`.name
		SET `release`.public = `source`.public
	"""
	)
