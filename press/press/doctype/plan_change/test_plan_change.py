# Copyright (c) 2022, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.press.doctype.press_settings.test_press_settings import create_test_press_settings
from press.press.doctype.server.test_server import create_test_server
from press.press.doctype.server_plan.test_server_plan import create_test_server_plan
from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


def create_server_plan_with_disk(disk: int) -> str:
	plan = create_test_server_plan()
	frappe.db.set_value("Server Plan", plan.name, "disk", disk)
	return plan.name


class TestPlanChange(FrappeTestCase):
	def setUp(self):
		create_test_press_settings()

	def tearDown(self):
		frappe.db.rollback()

	def create_server_with_disk(self, plan: str, disk_size: int):
		server = create_test_server(plan=plan)
		frappe.db.set_value("Virtual Machine", server.virtual_machine, "disk_size", disk_size)
		VirtualMachine("Virtual Machine", server.virtual_machine).update_subscription_for_addon_storage()
		return server

	def change_plan(self, server, from_plan: str, to_plan: str):
		frappe.get_doc(
			{
				"doctype": "Plan Change",
				"document_type": server.doctype,
				"document_name": server.name,
				"from_plan": from_plan,
				"to_plan": to_plan,
			}
		).insert()

	def addon_storage_subscription(self, server):
		return frappe.db.get_value(
			"Subscription",
			{"document_name": server.name, "plan_type": "Server Storage Plan"},
			["enabled", "additional_storage"],
			as_dict=True,
		)

	def test_upgrade_to_plan_with_larger_disk_shrinks_addon_storage(self):
		small_disk_plan = create_server_plan_with_disk(25)
		large_disk_plan = create_server_plan_with_disk(50)
		server = self.create_server_with_disk(small_disk_plan, disk_size=75)
		self.assertEqual(int(self.addon_storage_subscription(server).additional_storage), 50)

		self.change_plan(server, small_disk_plan, large_disk_plan)

		subscription = self.addon_storage_subscription(server)
		self.assertEqual(subscription.enabled, 1)
		self.assertEqual(int(subscription.additional_storage), 25)

	def test_downgrade_to_plan_with_smaller_disk_grows_addon_storage(self):
		small_disk_plan = create_server_plan_with_disk(25)
		large_disk_plan = create_server_plan_with_disk(50)
		server = self.create_server_with_disk(large_disk_plan, disk_size=75)
		self.assertEqual(int(self.addon_storage_subscription(server).additional_storage), 25)

		self.change_plan(server, large_disk_plan, small_disk_plan)

		subscription = self.addon_storage_subscription(server)
		self.assertEqual(subscription.enabled, 1)
		self.assertEqual(int(subscription.additional_storage), 50)

	def test_upgrade_to_plan_disk_larger_than_machine_disk_disables_addon_storage(self):
		small_disk_plan = create_server_plan_with_disk(25)
		larger_than_machine_plan = create_server_plan_with_disk(100)
		server = self.create_server_with_disk(small_disk_plan, disk_size=75)

		self.change_plan(server, small_disk_plan, larger_than_machine_plan)

		self.assertEqual(self.addon_storage_subscription(server).enabled, 0)
