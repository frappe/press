# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe

from press.press.doctype.enterprise_contract.enterprise_contract import create_contract
from press.press.doctype.enterprise_contract.test_enterprise_contract import EnterpriseContractTestCase


class TestOrderWaitsForTeamLock(EnterpriseContractTestCase):
	# Another connection only sees committed rows, so the team is committed and deleted afterwards.
	def setUp(self):
		frappe.db.rollback()
		self.team = self.commit_minimal_team()
		self.set_up_plan_and_bank_details()
		self.addCleanup(frappe.db.sql, "SET SESSION innodb_lock_wait_timeout = %s", self.lock_wait_timeout())
		frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 1")

	def commit_minimal_team(self):
		name = frappe.generate_hash(length=10)
		address = {"doctype": "Address", "name": name, "address_title": name}
		team = {
			"doctype": "Team",
			"name": name,
			"billing_name": name,
			"billing_address": name,
			"currency": "INR",
		}
		frappe.get_doc(address).db_insert()
		frappe.get_doc(team).db_insert()
		frappe.db.commit()
		self.addCleanup(self.delete_committed_team, name)
		return frappe._dict(name=name, currency="INR")

	def delete_committed_team(self, name: str):
		frappe.db.rollback()
		frappe.db.delete("Team", {"name": name})
		frappe.db.delete("Address", {"name": name})
		frappe.db.commit()

	def lock_wait_timeout(self) -> int:
		return frappe.db.sql("SELECT @@SESSION.innodb_lock_wait_timeout")[0][0]

	def test_order_waits_while_another_connection_holds_the_team_row_and_goes_through_after(self):
		other_connection = frappe.db.create_connection()
		self.addCleanup(other_connection.close)
		other_connection.cursor().execute(
			"SELECT name FROM tabTeam WHERE name = %s FOR UPDATE", (self.team.name,)
		)

		with self.assertRaises(frappe.QueryTimeoutError):
			create_contract(self.team, self.make_order())
		self.assertFalse(frappe.db.exists("Enterprise Contract", {"team": self.team.name}))

		other_connection.commit()
		contract = create_contract(self.team, self.make_order())
		self.assertEqual(contract.status, "Awaiting Payment")
