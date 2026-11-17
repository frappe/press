# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe

from press.api import enterprise_contract as contract_api
from press.press.doctype.enterprise_contract.enterprise_contract import EnterpriseContract, create_contract
from press.press.doctype.enterprise_contract.test_enterprise_contract import (
	EnterpriseContractTestCase,
	create_team_with_billing_address,
)
from press.press.doctype.server.server import BaseServer
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.server_plan.test_server_plan import create_test_server_plan
from press.press.doctype.team.test_team import create_test_team
from press.tests.test_staff_role_scopes import create_staff_user
from press.utils import is_partner_user


class TestContractAccess(EnterpriseContractTestCase):
	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	def create_partner_team(self):
		partner = create_test_team()
		frappe.db.set_value("Team", partner.name, {"erpnext_partner": 1, "partner_email": partner.user})
		return partner

	def test_any_customer_team_sees_the_plans_and_can_order(self):
		frappe.set_user(self.team.user)

		page = contract_api.get()
		self.assertEqual([p["name"] for p in page["plans"]], [self.plan.name])
		self.assertEqual((page["contracts"], page["premium_servers"]), ([], []))

		placed = contract_api.submit(self.make_order())
		self.assertEqual(
			frappe.db.get_value("Enterprise Contract", placed["contract"], "status"), "Awaiting Payment"
		)

	@patch.object(BaseServer, "after_insert", new=Mock())
	def test_team_with_a_premium_server_is_told_support_is_included(self):
		premium = create_test_server_plan()
		frappe.db.set_value("Server Plan", premium.name, "premium", 1)
		included = create_test_server(team=self.team.name, plan=premium.name)
		create_test_server(team=self.team.name, plan=create_test_server_plan().name)
		archived = create_test_server(team=self.team.name, plan=premium.name)
		frappe.db.set_value("Server", archived.name, "status", "Archived")
		frappe.set_user(self.team.user)

		self.assertEqual(
			contract_api.get()["premium_servers"], [{"name": included.name, "title": included.title}]
		)

	def test_partner_team_sees_why_it_cannot_order_and_its_order_is_rejected(self):
		partner = self.create_partner_team()
		frappe.db.set_value(
			"Team",
			partner.name,
			"billing_address",
			self.team.billing_address,
		)
		frappe.set_user(partner.user)

		self.assertEqual(contract_api.get()["order_blocked"], contract_api.PARTNER_ORDER_BLOCKED)
		with self.assertRaisesRegex(frappe.ValidationError, "Partners can't place Enterprise orders"):
			contract_api.submit(self.make_order())
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

	def test_contract_created_by_staff_needs_no_bank_details(self):
		team = create_team_with_billing_address("India")
		frappe.db.set_single_value("Press Settings", "bank_account_number", None)
		frappe.clear_document_cache("Press Settings", "Press Settings")

		contract = frappe.get_doc(doctype="Enterprise Contract", team=team.name, **self.make_order()).insert()

		self.assertEqual(contract.currency, "INR")
		self.assertEqual(contract.payment_gateway, "Bank Transfer")

	def test_staff_record_a_bank_transfer_by_utr_and_link_the_frappe_io_invoice(self):
		contract = frappe.get_doc(
			doctype="Enterprise Contract", team=self.team.name, **self.make_order()
		).insert()

		contract.confirm_bank_transfer(reference="utr000000000009")
		contract.payments[0].frappe_invoice = "ACC-SINV-2026-00042"
		contract.save()

		contract = EnterpriseContract("Enterprise Contract", contract.name)
		self.assertEqual(contract.status, "Pending Signature")
		self.assertIsNone(contract.transfer_reference)
		self.assertEqual(contract.payments[0].payment_reference, "UTR000000000009")
		self.assertEqual(contract.as_dashboard()["payments"][0]["frappe_invoice"], "ACC-SINV-2026-00042")

	def test_finance_staff_record_a_bank_transfer_and_support_staff_cannot(self):
		# A fresh copy: insert(ignore_permissions=True) leaves that flag on the created doc.
		contract = frappe.get_doc("Enterprise Contract", create_contract(self.team, self.make_order()).name)
		support = create_staff_user("Press Support L1")
		finance = create_staff_user("Press Finance")

		frappe.set_user(support)
		self.assertTrue(frappe.has_permission("Enterprise Contract", "read", contract.name))
		with self.assertRaises(frappe.PermissionError):
			contract.confirm_bank_transfer("UTR000000000011")

		frappe.set_user(finance)
		contract.confirm_bank_transfer("UTR000000000011")

		self.assertEqual(contract.status, "Pending Signature")

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
