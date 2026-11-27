# Copyright (c) 2026, Frappe and Contributors
# See license.txt
import unittest

import frappe

from press.tests.dashboard_request import DashboardRequestTestCase


class TestPartnerPaymentPayoutRequests(DashboardRequestTestCase):
	# The auth hook blocks this path for customers, and the endpoint has no ownership check yet
	@unittest.expectedFailure
	def test_payment_partner_submits_a_payout_and_is_still_logged_in(self):
		gateway = frappe.get_doc(
			{"doctype": "Payment Gateway", "gateway": frappe.mock("name"), "team": self.team.name}
		).insert(ignore_permissions=True)
		frappe.db.commit()
		self.login()

		# the Submit button on the New Payout page
		payout = self.post(
			"press.press.doctype.partner_payment_payout.partner_payment_payout.submit_payment_payout",
			{
				"partner": self.team.name,
				"payment_gateway": gateway.name,
				"from_date": "2026-01-01",
				"to_date": "2026-01-31",
				"partner_commission": 10,
				"transactions": [],
			},
		)

		self.assertSucceeded(payout)
		self.assertTrue(frappe.db.exists("Partner Payment Payout", {"partner": self.team.name}))
		self.assertStillLoggedIn()
