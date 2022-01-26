# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

"""
Suspend Sites of defaulter accounts.

This module deals with suspending sites of defaulters.

Defaulters are identified based on the following conditions:
- Is not a free account
- Is not an ERPNext Partner
- Card not added
- Does not have enough credit balance

The `execute` method is the main method which is run by the scheduler daily.
"""


import frappe
from frappe.utils.data import flt


def execute():
	teams_with_total_usage = get_teams_with_total_usage()

	for d in teams_with_total_usage:
		total_usage = d.total_usage
		team = frappe.get_doc("Team", d.team)

		if team.free_account or not total_usage or team.get_balance() > 0:
			continue

		total_usage_limit = get_total_free_usage_limit(team)

		# if total usage has crossed the allotted free credits, suspend their sites
		if total_usage > total_usage_limit:
			suspend_sites_and_send_email(team)


def suspend_sites_and_send_email(team):
	sites = team.suspend_sites(reason="Card not added and free credits exhausted")
	# send email
	if sites:
		email = team.user
		account_update_link = frappe.utils.get_url("/dashboard/welcome")
		frappe.sendmail(
			recipients=email,
			subject="Your sites have been suspended on Frappe Cloud",
			template="payment_failed",
			args={
				"subject": "Your sites have been suspended on Frappe Cloud",
				"account_update_link": account_update_link,
				"card_not_added": True,
				"sites": sites,
				"team": team,
			},
		)


def get_teams_with_total_usage():
	"""Find out teams which don't have a card, not a free account, not an erpnext partner with their total usage"""
	return frappe.db.sql(
		"""
		SELECT
			SUM(i.total) as total_usage,
			i.team
		FROM
			`tabInvoice` i
			LEFT JOIN `tabTeam` t ON t.name = i.team
		WHERE
			i.docstatus < 2
			AND ifnull(t.default_payment_method, '') = ''
			AND t.free_account = 0
			AND t.erpnext_partner = 0
		GROUP BY
			i.team
	""",
		as_dict=True,
	)


def get_total_free_usage_limit(team):
	"""Returns the total free credits allocated to the team"""
	if not team.free_credits_allocated:
		return 0

	settings = frappe.get_cached_doc("Press Settings", "Press Settings")
	return flt(
		settings.free_credits_inr if team.currency == "INR" else settings.free_credits_usd
	)
