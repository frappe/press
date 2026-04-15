# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from press.workflow_engine.doctype.press_workflow_kv.press_workflow_kv import (
	InMemoryKVStore,
	WorkflowKVStore,
)


class TestPressWorkflowKV(FrappeTestCase):
	def setUp(self):
		self.workflow_name = frappe.generate_hash(length=10)
		self.store = WorkflowKVStore(workflow_name=self.workflow_name)

	def tearDown(self):
		frappe.db.delete("Press Workflow KV", {"parent": self.workflow_name})
		frappe.db.delete("Press Workflow Object")

	def test_in_memory_kv_store(self):
		store = InMemoryKVStore()
		store.set("test_key", "test_value")
		self.assertEqual(store.get("test_key"), "test_value")

		store.delete("test_key")
		self.assertIsNone(store.get("test_key"))

	def test_workflow_kv_store_set_and_get(self):
		self.store.set("test_key", {"data": 123})

		value = self.store.get("test_key")
		self.assertEqual(value, {"data": 123})

	def test_workflow_kv_store_update(self):
		self.store.set("test_key", "initial_value")
		initial_kv_name = self.store._get_kv_record_name("test_key")
		initial_obj_name = frappe.db.get_value("Press Workflow KV", initial_kv_name, "value")

		self.store.set("test_key", "updated_value")
		updated_kv_name = self.store._get_kv_record_name("test_key")
		updated_obj_name = frappe.db.get_value("Press Workflow KV", updated_kv_name, "value")

		self.assertEqual(initial_kv_name, updated_kv_name)
		self.assertNotEqual(initial_obj_name, updated_obj_name)

		is_deleted = frappe.db.get_value("Press Workflow Object", initial_obj_name, "deleted")
		self.assertTrue(is_deleted)

		value = self.store.get("test_key")
		self.assertEqual(value, "updated_value")

	def test_workflow_kv_store_delete(self):
		self.store.set("test_key", "to_be_deleted")
		kv_name = self.store._get_kv_record_name("test_key")
		obj_name = frappe.db.get_value("Press Workflow KV", kv_name, "value")

		self.store.delete("test_key")

		self.assertFalse(frappe.db.exists("Press Workflow KV", kv_name))

		is_deleted = frappe.db.get_value("Press Workflow Object", obj_name, "deleted")
		self.assertTrue(is_deleted)

		self.assertIsNone(self.store.get("test_key"))

	def test_workflow_kv_store_get_nonexistent(self):
		self.assertIsNone(self.store.get("nonexistent_key"))
