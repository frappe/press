# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "usage_record")
	# PLE to Usage Record
	frappe.db.sql(
		"""
		insert into
			`tabUsage Record` (
				`name`,
				`creation`,
				`modified`,
				`modified_by`,
				`owner`,
				`team`,
				`document_type`,
				`document_name`,
				`date`,
				`plan`,
				`currency`,
				`amount`,
				`interval`,
				`invoice`,
				`remark`,
				`docstatus`
			)
		select
			CONCAT('UT', SUBSTR(ple.name, 4)),
			ple.creation,
			ple.modified,
			ple.modified_by,
			ple.owner,
			ple.team,
			'Site',
			ple.site,
			ple.date,
			ple.plan,
			ple.currency,
			ple.amount * -1,
			'Daily',
			ple.invoice,
			ple.remark,
			1
		from
			`tabPayment Ledger Entry` ple
		where
			ple.purpose = 'Site Consumption'
			and ple.docstatus = 1
			and ple.free_usage = 0
	"""
	)
