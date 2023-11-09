# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

"""
Suspend Sites of defaulter accounts.

This module deals with suspending sites of defaulters.

Defaulters are identified based on the following conditions:
- Is not a free account
- Is not a Legacy Partner account with payment mode as Partner Credits
- Has at least one unpaid invoice
- Has an active site

The `execute` method is the main method which is run by the scheduler on every 10th day of the month.
"""


import frappe


def execute():
	teams_with_unpaid_invoices = get_teams_with_unpaid_invoices()

	for d in teams_with_unpaid_invoices:
		team = frappe.get_doc("Team", d.team)

		if team.free_account or team.payment_mode == "Partner Credits":
			continue

		# suspend sites
		suspend_sites_and_send_email(team)


def suspend_sites_and_send_email(team):
	sites = team.suspend_sites(reason="Unpaid Invoices")
	# send email
	if sites:
		email = team.user
		frappe.sendmail(
			recipients=email,
			subject="Your sites have been suspended on Frappe Cloud",
			template="unpaid_invoices",
			args={
				"subject": "Your sites have been suspended on Frappe Cloud",
				"sites": sites,
			},
		)


def get_teams_with_unpaid_invoices():
	"""Find out teams which has active sites and unpaid invoices and not a free account"""
	return frappe.db.sql(
		"""
		SELECT DISTINCT
			i.team
		FROM
			`tabInvoice` i
			INNER JOIN `tabTeam` t ON t.name = i.team
			INNER JOIN `tabSite` s ON s.team = t.name
		WHERE
			s.status NOT IN ('Archived', 'Suspended')
			AND t.enabled = 1
			AND t.free_account = 0
			AND i.status = 'Unpaid'
			AND i.docstatus < 2
			AND i.type = 'Subscription'
	""",
		as_dict=True,
	)
