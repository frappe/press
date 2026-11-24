# Copyright (c) 2026, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


def create_test_bare_metal_inventory(public_ip_address: str = "203.0.113.10"):
	return frappe.get_doc(
		{
			"doctype": "Bare Metal Inventory",
			"public_ip_address": public_ip_address,
			"private_ip_address": "10.0.0.10",
			"bmc_ip_address": "10.1.0.10",
			"root_user": "root",
			"root_password": "root-secret",
			"bmc_user": "admin",
			"bmc_password": "bmc-secret",
		}
	).insert()


class TestBareMetalInventory(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_inventory_is_named_after_public_ip_address(self):
		inventory = create_test_bare_metal_inventory()
		self.assertEqual(inventory.name, "203.0.113.10")

	def test_root_and_bmc_passwords_are_stored_encrypted_and_readable(self):
		inventory = create_test_bare_metal_inventory()
		stored = frappe.db.get_value(
			"Bare Metal Inventory", inventory.name, ["root_password", "bmc_password"], as_dict=True
		)
		self.assertNotIn("secret", stored.root_password)
		self.assertNotIn("secret", stored.bmc_password)
		self.assertEqual(inventory.get_password("root_password"), "root-secret")
		self.assertEqual(inventory.get_password("bmc_password"), "bmc-secret")
