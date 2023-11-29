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
from press.utils import log_error


def execute():
	teams_with_unpaid_invoices = get_teams_with_unpaid_invoices()

	for d in teams_with_unpaid_invoices[:30]:
		team = frappe.get_doc("Team", d.team)

		if team.payment_mode == "Partner Credits":
			continue

		# suspend sites
		suspend_sites_and_send_email(team)


def suspend_sites_and_send_email(team):
	try:
		sites = team.suspend_sites(reason="Unpaid Invoices")
		frappe.db.commit()
	except Exception:
		log_error(
			f"Error while suspending sites for team {team.name}",
			traceback=frappe.get_traceback(),
		)
		frappe.db.rollback()
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


@frappe.whitelist()
def get_teams_with_unpaid_invoices():
	"""Find out teams which has active sites and unpaid invoices and not a free account"""
	plan = frappe.qb.DocType("Plan")
	query = (
		frappe.qb.from_(plan)
		.select(plan.name)
		.where(
			(plan.enabled == 1)
			& ((plan.is_frappe_plan == 1) | (plan.dedicated_server_plan == 1))
		)
	).run(as_dict=True)
	dedicated_or_frappe_plans = [d.name for d in query]

	invoice = frappe.qb.DocType("Invoice")
	team = frappe.qb.DocType("Team")
	site = frappe.qb.DocType("Site")

	query = (
		frappe.qb.from_(invoice)
		.inner_join(team)
		.on(invoice.team == team.name)
		.inner_join(site)
		.on(site.team == team.name)
		.where(
			(site.status).isin(["Active", "Inactive"])
			& (team.enabled == 1)
			& (team.free_account == 0)
			& (invoice.status == "Unpaid")
			& (invoice.docstatus < 2)
			& (invoice.type == "Subscription")
			& (site.free == 0)
			& (site.plan).notin(dedicated_or_frappe_plans)
		)
		.select(invoice.team)
		.distinct()
	)

	return query.run(as_dict=True)
