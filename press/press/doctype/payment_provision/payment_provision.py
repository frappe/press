# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, cint
from press.utils.stripe_controller import StripeController

class PaymentProvision(Document):
	pass

def setup_usage_record_with_stripe():
	date = add_days(getdate(), days=-1)

	for subs in frappe.get_all("Subscription", {"status": "Active"}, ['team']):
		sc = StripeController(team=subs.team)
		total_units = 0
		provisions = []
		for provision in frappe.get_all("Payment Provision", {
				"date": date,
				"pushed_to_stripe": 0,
				"team": subs
				}, ['*']
			):

			total_units += cint(provision.provisioned_qty)
			provisions.append(provision.name)

		sc.create_usage_record(qty=total_units)

		frappe.db.set_value("Payment Provision", {"name", ["in", provisions]}, 'pushed_to_stripe', 1)

def setup_payment_provision():
	for subs in frappe.get_all("Subscription", {"status": "Active"}, ['team']):
		for site in frappe.get_all("Site", {"team": subs.team, "status": "Active"}, ['name', 'plan']):
			if not frappe.db.exists("Payment Provision", {"data": getdate, "site": site.name}):
				plan_doc = frappe.get_cached_doc("Plan", site.plan)

				frappe.get_doc({
					"doctype": "Payment Provision",
					"site": site.name,
					"team": subs.team,
					"plan": site.plan,
					"date": getdate(),
					"provisioned_qty": plan_doc.get_units_to_charge(subs.team)
				}).insert()
