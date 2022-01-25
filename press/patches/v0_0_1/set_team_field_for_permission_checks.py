# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	updates = [
		["Site Domain", "Site", "site"],
		["App Release", "App Source", "source"],
		["Deploy Candidate", "Release Group", "group"],
		["Deploy Candidate Difference", "Release Group", "group"],
		["Deploy", "Release Group", "group"],
		["Bench", "Release Group", "group"],
	]
	for target_doctype, source_doctype, link_fieldname in updates:
		frappe.reload_doc("press", "doctype", frappe.scrub(target_doctype))
		frappe.db.sql(
			f"""
			UPDATE `tab{target_doctype}` as target
			INNER JOIN `tab{source_doctype}` as source
			ON `target`.`{link_fieldname}` = `source`.`name`
			SET `target`.team = `source`.team
			WHERE ifnull(`target`.team, '') = ""
		"""
		)
