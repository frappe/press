# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe

from press.api import enterprise_contract as contract_api
from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract
from press.press.doctype.enterprise_contract.test_enterprise_contract import (
	EnterpriseContractTestCase,
	create_team_with_billing_address,
)
from press.press.doctype.team.test_team import create_test_team
from press.utils import is_partner_user


class TestContractAccess(EnterpriseContractTestCase):
	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	def create_partner_team(self):
		partner = create_test_team()
		frappe.db.set_value("Team", partner.name, {"erpnext_partner": 1, "partner_email": partner.user})
		return partner

	def test_contracts_api_rejects_a_team_without_contracts_enabled(self):
		frappe.db.set_value("Team", self.team.name, "enable_enterprise_contracts", 0)
		frappe.set_user(self.team.user)

		with self.assertRaisesRegex(frappe.ValidationError, "not enabled for this team"):
			contract_api.get()
		with self.assertRaisesRegex(frappe.ValidationError, "not enabled for this team"):
			contract_api.submit(self.make_order(), return_url="https://press.test/contracts")
		self.assertFalse(frappe.db.exists("Enterprise Contract", {"team": self.team.name}))

	def test_partner_team_sees_why_it_cannot_order_and_its_order_is_rejected(self):
		partner = self.create_partner_team()
		frappe.db.set_value(
			"Team",
			partner.name,
			{"enable_enterprise_contracts": 1, "billing_address": self.team.billing_address},
		)
		frappe.set_user(partner.user)

		self.assertEqual(contract_api.get()["order_blocked"], contract_api.PARTNER_ORDER_BLOCKED)
		with self.assertRaisesRegex(frappe.ValidationError, "Partners can't place Enterprise orders"):
			contract_api.submit(self.make_order(), return_url="https://press.test/contracts")
		self.assertFalse(frappe.db.exists("Enterprise Contract", {"team": partner.name}))

	def test_member_of_a_partner_team_counts_as_a_partner_in_a_customer_team(self):
		partner = self.create_partner_team()
		member = create_test_team().user
		frappe.get_doc(
			doctype="Team Member",
			parent=partner.name,
			parenttype="Team",
			parentfield="team_members",
			user=member,
		).db_insert()

		self.assertTrue(is_partner_user(member))
		self.assertTrue(is_partner_user(partner.user))
		self.assertFalse(is_partner_user(self.team.user))

	def test_staff_acting_in_a_partner_team_cannot_order_for_it(self):
		partner = frappe.get_doc("Team", self.create_partner_team().name)

		self.assertFalse(is_partner_user("Administrator"))
		self.assertTrue(contract_api.acts_as_partner(partner))

	def test_contract_created_by_staff_needs_no_bank_details_and_shows_on_the_teams_dashboard(self):
		team = create_team_with_billing_address("India")
		frappe.db.set_value("Team", team.name, "enable_enterprise_contracts", 0)
		frappe.db.set_single_value("Press Settings", "bank_account_number", None)
		frappe.clear_document_cache("Press Settings", "Press Settings")

		contract = frappe.get_doc(doctype="Enterprise Contract", team=team.name, **self.make_order()).insert()

		self.assertEqual(contract.currency, "INR")
		self.assertEqual(contract.payment_gateway, "Bank Transfer")
		self.assertEqual(frappe.db.get_value("Team", team.name, "enable_enterprise_contracts"), 1)

	def test_staff_record_a_bank_transfer_by_utr_and_link_the_frappe_io_invoice(self):
		contract = frappe.get_doc(
			doctype="Enterprise Contract", team=self.team.name, **self.make_order()
		).insert()

		contract.confirm_bank_transfer(reference="utr000000000009")
		contract.payments[0].frappe_invoice = "ACC-SINV-2026-00042"
		contract.save()

		contract = EnterpriseContract("Enterprise Contract", contract.name)
		self.assertEqual(contract.status, "Pending Signature")
		self.assertEqual(contract.transfer_reference, "UTR000000000009")
		self.assertEqual(contract.payments[0].payment_reference, "UTR000000000009")
		self.assertEqual(contract.as_dashboard()["payments"][0]["frappe_invoice"], "ACC-SINV-2026-00042")

	def test_staff_cannot_create_a_contract_while_the_team_has_an_order_waiting_for_payment(self):
		order = frappe.get_doc(
			doctype="Enterprise Contract", team=self.team.name, **self.make_order()
		).insert()
		order.submit_transfer_reference("UTR000000000011")

		with self.assertRaisesRegex(frappe.ValidationError, f"order {order.name} waiting for payment"):
			frappe.get_doc(doctype="Enterprise Contract", team=self.team.name, **self.make_order()).insert()
		self.assertEqual(order.reload().status, "Awaiting Payment")

	def test_print_format_shows_the_customer_plan_and_payment_with_its_tax_invoice(self):
		frappe.db.set_single_value("Press Settings", "gst_home_state", "Karnataka")
		frappe.clear_document_cache("Press Settings", "Press Settings")
		contract = frappe.get_doc(
			doctype="Enterprise Contract", team=self.team.name, **self.make_order()
		).insert()
		contract.confirm_bank_transfer(reference="UTR000000000010")
		contract.payments[0].frappe_invoice = "ACC-SINV-2026-00043"
		contract.save()

		html = frappe.get_print("Enterprise Contract", contract.name, "Enterprise Contract")

		for text in ("Acme Industries", self.plan.title, "UTR000000000010", "ACC-SINV-2026-00043", "IGST"):
			self.assertIn(text, html)
