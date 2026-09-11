# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.agent import Agent
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

	def test_owner_can_save_the_whole_document_the_dashboard_read(self):
		"""frappe-ui posts back every field it read, standard ones included."""
		owner = self.firewall.owner
		document = {
			"owner": "somebody@example.com",
			"creation": "2026-08-26 21:51:49.591602",
			"modified": "2026-08-26 21:51:49.591602",
			"modified_by": "somebody@example.com",
			"docstatus": 1,
			"idx": 0,
			"enabled": 1,
			"rules": [{"source": "173.245.48.0/20", "port": 443, "protocol": "TCP", "action": "Allow"}],
			"tabs_access": {},
			"actions_access": {},
		}

		sign_in_as(self.team)
		set_value("Server Firewall", self.firewall.name, document)

		saved = frappe.get_doc("Server Firewall", self.firewall.name)
		self.assertEqual(saved.enabled, 1)
		self.assertEqual([rule.source for rule in saved.rules], ["173.245.48.0/20"])
		self.assertEqual(saved.owner, owner)
		self.assertEqual(saved.docstatus, 0)

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


class TestServerFirewallNginxSync(FrappeTestCase):
	"""Nginx cannot tell a visitor from the proxy unless the sync carries the proxy IP."""

	def setUp(self):
		super().setUp()
		self.server = create_test_server()
		self.firewall = frappe.get_doc("Server Firewall", {"server_id": self.server.name})
		self.firewall.append(
			"rules", {"source": "183.82.5.84/32", "port": 443, "protocol": "TCP", "action": "Allow"}
		)
		self.firewall.append(
			"rules", {"source": "0.0.0.0/0", "port": 443, "protocol": "TCP", "action": "Deny"}
		)
		self.firewall.enabled = 1
		self.firewall.save()

	def tearDown(self):
		frappe.db.rollback()

	@patch.object(Agent, "update_nginx_access")
	def test_nginx_sync_sends_the_proxy_ip_along_with_the_rules(self, update_nginx_access):
		self.firewall._sync_nginx()

		ip_accept, ip_drop, proxy_ip = update_nginx_access.call_args.args
		self.assertIn("183.82.5.84/32", ip_accept)
		self.assertEqual(ip_drop, ["0.0.0.0/0"])
		self.assertEqual(proxy_ip, self.server.get_proxy_ip())

	@patch.object(Agent, "update_nginx_access")
	def test_the_proxy_subnet_the_sync_allows_is_the_one_it_asks_nginx_to_trust(self, update_nginx_access):
		"""Allowing the subnet without trusting it is what let every visitor through."""
		self.firewall._sync_nginx()

		ip_accept, _, proxy_ip = update_nginx_access.call_args.args
		self.assertIn(proxy_ip, ip_accept)
