# Copyright (c) 2025, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.add_on_storage_log.add_on_storage_log import (
	disk_space_actions,
	monthly_storage_cost,
)
from press.press.doctype.server.test_server import create_test_server


class TestAddOnStorageLog(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.server = create_test_server()
		self.database_server = frappe.get_doc("Database Server", self.server.database_server)
		self.storage_plan = self.enabled_storage_plan()

	def tearDown(self):
		frappe.db.rollback()

	def enabled_storage_plan(self) -> str:
		name = frappe.db.get_value("Server Storage Plan", {"enabled": 1})
		if not name:
			name = (
				frappe.get_doc({"doctype": "Server Storage Plan", "title": "Test Storage", "enabled": 1})
				.insert(ignore_permissions=True)
				.name
			)
		frappe.db.set_value("Server Storage Plan", name, {"price_usd": 0.1, "price_inr": 8})
		return name

	def test_app_server_disk_email_links_to_cleanup_server_and_overview(self):
		links = {link["label"]: link["url"] for link in disk_space_actions(self.server)}

		page = frappe.utils.get_url(f"/dashboard/servers/{self.server.name}")
		self.assertEqual(links["Cleanup Server"], f"{page}/actions?action=Cleanup%20Server")
		self.assertEqual(links["Storage and Auto Increase Storage settings"], f"{page}/overview")

	def test_database_server_disk_email_links_to_binlog_actions_on_app_server_page(self):
		links = {link["label"]: link["url"] for link in disk_space_actions(self.database_server)}

		page = frappe.utils.get_url(f"/dashboard/servers/{self.server.name}")
		self.assertEqual(
			links["Manage Database Binlogs"], f"{page}/actions?action=Manage%20Database%20Binlogs"
		)
		self.assertEqual(
			links["Update Binlog Size Limit"], f"{page}/actions?action=Update%20Binlog%20Size%20Limit"
		)
		self.assertNotIn("Cleanup Server", links)

	def test_monthly_storage_cost_uses_team_currency_price_per_gb(self):
		frappe.db.set_value("Team", self.server.team, "currency", "USD")
		self.assertEqual(monthly_storage_cost(self.server, 50), frappe.utils.fmt_money(5, currency="USD"))

		frappe.db.set_value("Team", self.server.team, "currency", "INR")
		self.assertEqual(monthly_storage_cost(self.server, 50), frappe.utils.fmt_money(400, currency="INR"))

	@patch("press.press.doctype.add_on_storage_log.add_on_storage_log.frappe.sendmail")
	def test_auto_increase_email_states_monthly_cost_and_links(self, sendmail):
		frappe.db.set_value("Team", self.server.team, "currency", "USD")
		log = frappe.get_doc(
			{
				"doctype": "Add On Storage Log",
				"server": self.server.name,
				"adding_storage": 20,
				"available_disk_space": 100,
				"current_disk_usage": 91,
				"is_warning": 0,
			}
		).insert(ignore_permissions=True)

		log.send_notification()

		email = sendmail.call_args.kwargs
		self.assertEqual(email["template"], "enabled_auto_disk_expansion")
		self.assertEqual(email["args"]["monthly_cost"], frappe.utils.fmt_money(2, currency="USD"))
		self.assertIn("Cleanup Server", [link["label"] for link in email["args"]["actions"]])
