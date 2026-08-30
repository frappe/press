# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.api.client import set_value
from press.api.tests.test_client import sign_in_as
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.team.test_team import create_test_press_admin_team


class TestServerFirewallDashboardEditing(FrappeTestCase):
	"""The firewall page saves the switch and the rules table through `set_value`."""

	def setUp(self):
		super().setUp()
		self.team = create_test_press_admin_team()
		self.server = create_test_server(team=self.team.name)
		self.firewall = frappe.get_doc("Server Firewall", {"server_id": self.server.name})

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_owner_can_enable_the_firewall_from_the_dashboard(self):
		sign_in_as(self.team)
		set_value("Server Firewall", self.firewall.name, {"enabled": 1})

		self.assertEqual(frappe.db.get_value("Server Firewall", self.firewall.name, "enabled"), 1)

	def test_owner_can_write_the_rules_table_from_the_dashboard(self):
		rules = [
			{"source": "173.245.48.0/20", "port": 443, "protocol": "TCP", "action": "Allow"},
			{"source": "103.21.244.0/22", "port": 443, "protocol": "TCP", "action": "Allow"},
		]

		sign_in_as(self.team)
		set_value("Server Firewall", self.firewall.name, {"enabled": 1, "rules": rules})

		saved = frappe.get_doc("Server Firewall", self.firewall.name)
		self.assertEqual([rule.source for rule in saved.rules], [rule["source"] for rule in rules])

	def test_another_team_cannot_write_the_rules_table(self):
		other_team = create_test_press_admin_team()

		sign_in_as(other_team)
		with self.assertRaises(frappe.PermissionError):
			set_value("Server Firewall", self.firewall.name, {"enabled": 1})

		self.assertEqual(frappe.db.get_value("Server Firewall", self.firewall.name, "enabled"), 0)

	def test_server_id_stays_out_of_reach_from_the_dashboard(self):
		other_server = create_test_server(team=self.team.name)

		sign_in_as(self.team)
		with self.assertRaises(frappe.PermissionError):
			set_value("Server Firewall", self.firewall.name, {"server_id": other_server.name})

		self.assertEqual(
			frappe.db.get_value("Server Firewall", self.firewall.name, "server_id"), self.server.name
		)
